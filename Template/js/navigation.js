$(function() {
        // add zoom out button 

        var options = {
            series: {
                lines: {
                    show: true
                },
                points: {
                    show: true
                }
            },
            xaxis: {
                tickDecimals: 0,
                tickSize: 1
            },
            zoom: {
                interactive: true
            },
            pan: {
                interactive: true
            }
        };
        var data = [];
        var navi_map = $("#navi_map");

        $.plot(navi_map, data, options);


        // fetch one series, adding to what we got
        var alreadyFetched = {};


        // then fetch the data with jQuery

        function onDataReceived(series) {
            console.log("onDataReceived");


            if (!alreadyFetched[series.label]) {
                alreadyFetched[series.label] = true;
                data.push(series);
            } else {
                if (series.label == 'nextPoint') {

                    var dl = data.length;
                    for (var i = 0; i < dl; i++) {
                        if (data[i].label == series.label) {
                            data[i].data = series.data;
                        }
                    }
                } else {


                    var dl = data.length;
                    for (var i = 0; i < dl; i++) {
                        if (data[i].label == series.label) {
                            data[i].data = data[i].data.concat(series.data);
                        }
                    }
                }
            }


            $.plot(navi_map, data, options);
            console.log("puntos pintados");
        }



    $("#do_route").click(function() {
        console.log('do_route');
        socket.send({
            action: 'do_route',
            'route_id': 4
        });
    });

    var messaged = function(rxdata) {
        console.log("messaged_data_navigation");
        console.log(data);
        switch (rxdata.action) {
            case 'route':
                onDataReceived(rxdata.series);
                break;

            case 'coord_inLine':
                onDataReceived(rxdata.series);
                break;

            case 'gpsInfo':
                console.log(rxdata.gpsData);
                if (rxdata.gpsData != '') {
                    var series = {
                        label: 'GPS',
                        data: [
                            [rxdata.gpsData.lat, rxdata.gpsData.lon]
                        ]
                    };
                    onDataReceived(series);
                }
                break;

            case 'do_route':
            console.log(rxdata.gpsData);
                //console.log(data);
                //socket.broadcast_channel({"action": "do_route", "gpsData": gpsData,
                //"nextPoin": point, 'distance_to': dist}, 'navigation')
                var upData = {
                    label: 'nextPoint',
                    data: [rxdata.nextPoint, [rxdata.gpsData.lat, rxdata.gpsData.lon]]
                }
                onDataReceived(upData);
                if (rxdata.gpsData != '') {
                    var series = {
                        label: 'GPS',
                        data: [
                            [rxdata.gpsData.lat, rxdata.gpsData.lon]
                        ]
                    };
                    onDataReceived(series);
                }
                console.log("DOXROUTE");
                break;

            default:
                console.log("BlaBlaBLa");

        }
    };

    var connected = function() {
        console.log("connected");
        socket.subscribe('navigation');

        //socket.send({hola:"hola hola->"});
        socket.send({
            action: 'get_route'
        });
        //get_gps_data();
    };

    var get_gps_data = function() {
        socket.send({
            action: 'get_gps_data'
        });
        //setTimeout(get_gps_data, 3000);
    }

    var disconnected = function() {
        console.log("disconnected");
        setTimeout(start, 1000);
    };

    var start = function() {
        socket = new io.Socket();
        socket.connect();
        socket.on('connect', connected);
        socket.on('disconnect', disconnected);
        socket.on('message', messaged);
    };

    start();


});