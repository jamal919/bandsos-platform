# Running BandSOS system
Scripting the BandSOS system is quite easy, thanks to the python programming language. The script is run in a system or 
docker environment where `bandsos` library is installed. Please see the `examples` folder in the repository for some
demonstration how the scripts can be developed. 

.. note::
    In the alpha version, the full workflow is needed to be integrated into the running script. In future development
    of the interface, more concise version is planned to be developed.

## Hindcast
```
{
    'cycle':'yyyymmddhh',
    'producer':'producer',
    'status':'ongoing' <ongoing, failed, done, published>,
    'lastupdate':'2020-05-17 00:00:00'
    'lastforecast':{
                'date':'2020-05-17',
                'cycle':'00'
            }
}
```
## Forecast