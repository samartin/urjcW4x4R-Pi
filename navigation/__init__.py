import threading
import logging
import time
import sys
import gps
from django_socketio import broadcast_channel
from django_socketio import NoSocket
from coord import *
from navigation.models import Route, Coord

class StartGps(object):
    def __init__(self):
        self.gpsData = {}
        try:
            self._gps = gps.gps(mode=gps.WATCH_ENABLE | gps.WATCH_JSON | gps.WATCH_NEWSTYLE)
        except:  # except (StopIteration):
            print "Unexpected error:", sys.exc_info()[0]
            self._gps = {}
            pass


    def update(self):
        try:
            self._gps.next()
        except StopIteration:
            print "Unexpected error: StartGps: ", sys.exc_info()[0]
            pass    
        except AttributeError:  # Hay que decidir que hacer si se produce un error.
            return      {'lat' :   0,
                        'lon'   :   0,
                        'track' :   0,
                        'speed' :   0,
                        'time'  :   0,  # le pasa algo raro
                        # 'date'     :   self._gps.fix.date,
                        # 'alt'  :   self._gps.fix.altitude,
                        }

        return  {'lat' :   self._gps.fix.latitude,
                'lon'   :   self._gps.fix.longitude,
                'track' :   self._gps.fix.track,
                'speed' :   self._gps.fix.speed,
                'time'  :   self._gps.fix.time,  # le pasa algo raro
                # 'date'     :   self._gps.fix.date,
                # 'alt'  :   self._gps.fix.altitude,
                }

class BrodcastThread(threading.Thread):
    def run(self):
        time.sleep(5);
        while True:
            time.sleep(0.2);
            gpsInfo = _gps.update()
            try:
                broadcast_channel({'action':'gpsInfo', 'gpsData': gpsInfo}, 'navigation')
            except NoSocket:
                time.sleep(5);
            
# thread.start_new_thread(print_time, ("Thread-1", 2, socket))

class RouteThread(threading.Thread):

    def __init__(self, route_id):
        super(RouteThread, self).__init__()
        self.route_id = route_id
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
    
    def run(self):
        route_id = self.route_id;
        print route_id
        time.sleep(1);
        
        try:
            broadcast_channel({'action':'startRoute -AA'}, 'navigation')
            time.sleep(1);
        except NoSocket:
            time.sleep(5);
        except:
            raise
        try:
            rout = Route.objects.get(id=route_id)
            coords = Route.get_only_coord(rout)
            for point in coords:
                try:
                    vehicle.speed(96)#velocidad minima
                except:
                    pass
                reached = False;
                infopoint={'action':'next_point', 'lat': point[0], 'lon': point[1]}
                broadcast_channel(infopoint, 'navigation')
                while not reached and not self.stopped():
                    gpsData = _gps.update()
                    if str(gpsData['track']) != "nan":
                        dist = distance_to(point, gpsData)
                        H=heading_to(point, gpsData)
                        angle_diff = get_angle_diff(gpsData['track'], H)
                        turn_angle = angle_to_turn_angle(angle_diff) #lo devuelve como int
                        try:
                            vehicle.turn(turn_angle)
                        except:
                            pass
                        infopoint={'action':'state_route', 'lat': gpsData['lat'], 'lon': gpsData['lon'], 'dist': dist}
                        broadcast_channel(infopoint, 'navigation')
                        print 'gpsData: ' + str(gpsData['lat']) + ' ' + str(gpsData['lon']) + ' Next point: ' + str(point) + ' Distance: ' +str(dist) + ' Turn angle: ' + str(turn_angle)
                        # socket.send({"action": "dox_route", "gpsData": gpsData,"nextPoin": point, 'distance_to': dist})
                        if dist < 300 and dist != -1:
                            reached = True
                            print '================ FIESTA =================== PUNTO ALCANZADO'
            if not self.stopped():#porque ya lo hago en events
                print "Ruta terminada"
                _thrd['RouteThread'].stop()
                del _thrd['RouteThread']
                rs.started=0
                vehicle.reset()
                broadcast_channel({'action':'routeIsStopped'}, 'navigation')
      
        except:
            raise

class RouteState(object):
    def __init__ (self):
        self.started = 0
        self.id = -1

class Control(object):
    def __init__ (self):
        self.ws_value = 90
        self.ad_value = 90
        
        # Paso del incremento
        self.inc = 1;
        
        try:
            self.arduino_conect = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
        except:  # except (StopIteration):
            print "Unexpected error: Control ", sys.exc_info()[0]
            self.arduino_conect = ''
            pass
        
        self.reset()
        
        
    def reset(self):
        self.ws_value = 90
        self.ad_value = 90
        self.set(self.ws_value, self.ad_value)
        
    def action(self, action):
        if action == 'w':
            self.ws_value += self.inc
        elif action == 's':
            self.ws_value -= self.inc
        elif action == 'd':
            self.ad_value += self.inc
        elif action == 'a':
            self.ad_value -= self.inc
        else:  # action == 'q':
            # por medidas de seguridad, si el coche se escapa 
            # y/o el piloto se pone nervioso
            self.reset()
        
        self.evalue_wa()
        self.set(self.ws_value, self.ad_value)
        
        #devolver el valor, el que se ha pasado al coche
        return self.ws_value, self.ad_value
            
    def set(self, speed, angle):
        

        print 'Vehicle: s-' + str(speed) + ' a-' + str(angle)
        
        if self.arduino_conect != '':
            self.speed(speed)
            self.turn(angle)
        
    def speed(self, velocidad):
            self.arduino_conect.write(chr(255))
            self.arduino_conect.write(chr(2))
            self.arduino_conect.write(chr(velocidad))


    def turn(self, grados):
            self.arduino_conect.write(chr(255)) 
            self.arduino_conect.write(chr(1))
            self.arduino_conect.write(chr(grados))
            
    def evalue_wa(self):
        if self.ws_value > 120:
            self.ws_value = 120
        elif self.ws_value < 60:
            self.ws_value = 60
        
        if self.ad_value > 120:
            self.ad_value = 120
        elif self.ad_value < 60:
            self.ad_value = 60



_thrd = dict()

_gps = StartGps();

bth = BrodcastThread()
bth.setDaemon(True)
bth.start()

rs = RouteState()

vehicle = Control()