from pyrfc3339 import generate, parse
import vcoclient

from influxdb import InfluxDBClient

# Create our influx db client connection
influx = InfluxDBClient(host='localhost', port=8086)
influx.create_database('vco')

# Create a VCO client
vco_client = vcoclient.VcoClient('<your vco goes here>')



def pull_app_series_metrics(client):
    edges = client.getEnterpriseEdges(0)

    tsd = []
    # Iterate over each edge
    for e in edges:
        # Influx line protocol requires that tag's have escaped spaces
        # this line escapes out any spaces in the edge name
        influx_edge_name = e['name'].replace(" ", '\\ ')

        # Grab a list of apps that the edge has seen over the last 12 hours
        app_list = client.get_edge_app_metrics(0, e['id'])

        # Generate a list of those applications
        app_series = []
        for app in app_list:
            app_series.append(str(app['application']))


        # Grab the time series flow data from the orchestrator
        apps = client.get_edge_app_series(0, e['id'], metrics=["bytesTx", "bytesRx"],
                                          applications=app_series)

        # Iterate over each application and create a generate a data point for each metric
        for app in apps:
            # Escape spaces and commas from the app name
            influx_app_name = app['name'].replace(" ", '\\ ').replace(",", "\,")
            for metric in app['series']:
                start_time = parse(metric['startTime']).timestamp()
                for d in metric['data']:
                    point = ("veloAppSeries,edgeName={edgeName},appName={appName}"
                             " {metric}={measurement}"
                             " {timestamp}").format(edgeName=influx_edge_name,
                                                    appName=influx_app_name,
                                                    metric=metric['metric'],
                                                    measurement=d,
                                                    timestamp=int(start_time)
                                                    )
                    tsd.append(point)
                    start_time = start_time + (metric['tickInterval']/1000)

    # Write the metrics to influx
    influx.write_points(tsd,database="vco", time_precision='s', batch_size=10000, protocol='line')

if __name__ == '__main__':
    pull_app_series_metrics(vco_client)
