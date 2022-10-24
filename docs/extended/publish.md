# Publishing Online

## Github/Github pages
- Creating an account
- Cloning the website
- Setup github pages

## Folder structure
```
|- fluxes
    |- netcdf
        |- gfs.nc
    |- tracks
        |- bioxxxxxx.dat
        |- aioxxxxxx.dat
|- advisories
    |- jtwc
|- forecasts
    |- elev
        |- tiles
            |- 2022010100
            |- 2022010103
            |- ...
            |- etc.
        |- stations
            |- WL001.csv
            |- WL002.csv
            |- etc.
    |- maxelev
        |- tiles
            |- 20220101
            |- 20220102
            |- 20220103
            |- ...
            |- etc.
    |- risk
        |- tiles
            |- 20220101
            |- 20220102
            |- 20220103
            |- ...
            |- etc.
    |- track
        |- forecast.json
        |- best.json
        |- model.json
```

## manifest.json
```json
[
    "cycle":"2022020100",
    "date":"yyyy-mm-dd HH:MM:SS",
    "lastupdate":"yyyy-mm-dd HH:MM:SS",
    "producer":"FFWC/BWDB",
    "version":"0.1",
    "advisories":[
        {
            "name":"JTWC",
            "agency":"JTWC",
            "source":"https://www.metoc.navy.mil/jtwc/jtwc.html",
            "src":"advisories/jtwc.dat"
        }
    ],
    "fluxes":[
        {
            "name":"GFS 0.25 deg",
            "type":"netcdf",
            "available":true,
            "source":"NOAA/NCEP",
            "src":"fluxes/netcdf/gfs.nc"
        },
        {
            "name":"NOAA/NCEP",
            "type":"atcf",
            "available":true,
            "source":"NOAA/NCEP",
            "src":"fluxes/tracks/aio_yyyymmddhh.dat"
        },
        {
            "name":"JTWC/BEST Track",
            "type":"atcf",
            "available":true,
            "source":"NOAA/NCEP",
            "src":"fluxes/tracks/bio_yyyymmddhh.dat"
        },
        {
            "name":"HWRF",
            "type":"atcf",
            "available":true,
            "source":"NOAA/NCEP",
            "src":"fluxes/tracks/hwrf_yyyymmddhh.dat"
        }
    ],
    "forecasts":[
        {
            "name":"Water level",
            "src":"forecasts/elev",
            "layers": [
                {
                    "name":"Map",
                    "type":"tiles",
                    "timeseries":true,
                    "colorbar":true,
                    "colorbar_file":"colorbar.png",
                    "colorscale":[{"value":"color"}],
                    "timestamps":[
                        {
                            "time":"2020-05-15 03:00:00",
                            "folder":"2020051503"
                        },
                        {
                            "etc"
                        }
                    ]
                },
                {
                    "name":"Water level",
                    "type":"stations",
                    "stations":[
                        {
                            "id": "WL062", 
                            "lon": 89.8044, 
                            "lat": 22.6486, 
                            "name": "Bagerhat", 
                            "org": "BWDB",
                            "status": "unknown",
                        }
                    ]
                }
            ],

        },
        {
            "name":"Water level (maximum)",
            "src":"forecasts/maxelev",
            "layers": [
                {
                    "name":"Map",
                    "type":"tiles",
                    "timeseries":true,
                    "colorbar":true,
                    "colorscale":{
                        [
                            "value":"color"
                        ]
                    },
                    "timestamps":[
                        {
                            "time":"2020-05-15",
                            "folder":"20200515"
                        },
                        {
                            "etc"
                        }
                    ]
                }
            ]
        },
        {
            "name":"Risk",
            "src":"forecasts/risk",
            "layers": [
                {
                    "type":"tiles",
                    "timeseries":true,
                    "colorbar":true,
                    "colorscale":{
                        [
                            "value":"color"
                        ]
                    },
                    "timestamps":[
                        {
                            "time":"2020-05-15",
                            "folder":"20200515"
                        },
                        {
                            "etc"
                        }
                    ]
                }
            ]
        }
    ],
    "tracks":[
        {

        },
        {
            
        }
    ]
]
```