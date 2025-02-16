let marketTime = js_vars.marketTime*13

function redrawChart(series) {
        Highcharts.chart('highchart', {

            title: {
                text: 'Historial de Precio'
            },
            yAxis: {
                title: {
                    text: 'Precio'
                }
            },
            xAxis: {
                title: {
                    text: 'Tiempo (segundos)'
                },
                min: 0,
                max: marketTime ,
            },
            legend: {
                enabled: true
            },

            plotOptions: {
                series: {
                    label: {
                        enabled: true
                    },
                }
            },

            series: series,

            credits: {
                enabled: false
            }
        });
    }