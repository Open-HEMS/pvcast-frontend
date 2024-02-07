# How to configure the application

To get accurate forecasts we need to provide the necessary information to the PV model. This may take some time, but luckily it only has to be done once 🎉.

## Validating the configuration

After creating a config you can check the **`✔️ CONFIG VALIDATOR`** tab in the UI to see if the config is valid. If it's not valid, the UI will tell you what's wrong with it.

## The configuration file

The configuration is stored in a YAML file called `config.yaml`. The configuration file is read by the pvcast model to determine the parameters and composition of your PV system. It contains information about the arrays and inverters that make up your PV system. 

An example of a `config.yaml` file is shown below:

```yaml
plant:
  - name: EastWest
    inverter: SolarEdge_Technologies_Ltd___SE4000__240V_
    microinverter: false
    arrays:
      - name: East
        tilt: 30
        azimuth: 90
        modules_per_string: 4
        strings: 1
        module: Trina_Solar_TSM_330DD14A_II_
      - name: West
        tilt: 30
        azimuth: 270
        modules_per_string: 8
        strings: 1
        module: Trina_Solar_TSM_330DD14A_II_ 
```

## PV plants

The PV plants are defined in the `plant` section of the configuration file. Each PV plant can be thought of as an independent PV installation with a set of PV arrays connected to a single PV inverter. For example, if you have one inverter with 2 arrays, you would define one PV plant with 2 arrays. If you have 2 inverters with 2 arrays each, you would define 2 PV plants with 2 arrays each. This is important because inverters have a limited number of MPPT inputs and the model needs to know which arrays are connected to which inverter. There is no limit to how many PV plants can be set.

Each PV plant is defined by a map with the following keys:

- **name** (string): The name of the PV plant. This name is used to identify the PV plant in the logs and in the API. It must be unique
- **inverter** (string): The inverter identifier string. The inverter must be one of the inverters listed [here](https://github.com/Open-HEMS/pvcast/blob/main/pvcast/data/proc/cec_inverters.csv). You can use the UI to search for your specific inverter.
- **microinverter** (boolean): Whether the inverter is a microinverter, for example Enphase IQ inverters. If this is set to `true`, the model will assume that each array is connected to a separate inverter. If this is set to `false`, the model will assume that all arrays are connected to the same inverter.
- **arrays** (list): A list of PV arrays that make up the PV plant. See [PV arrays](#pv-arrays) for more information.
  - **name** (string): The name of the PV array. This name is used to identify the PV array in the logs.
  - **tilt** (float): The tilt of the PV array in degrees. This is the angle between the PV array and the horizontal plane. A tilt of 0 means that the PV array is horizontal. A tilt of 90 means that the PV array is vertical.
  - **azimuth** (float): The azimuth of the PV array in degrees clockwise from North. A value of 180 degrees means that the PV array is facing south.
  - **modules_per_string** (int): The number of PV modules per string.
  - **strings** (int): The number of strings in the PV array.
  - **module** (string): The name of the PV module. The PV module must be one of the PV modules listed [here](https://github.com/Open-HEMS/pvcast/blob/main/pvcast/data/proc/cec_modules.csv), same process as the inverter.

## Important notes

- It's okay if you don't know how many strings are connected to your inverter. The most important thing is to have the correct number of panels (modules). If you don't know how many strings are connected to your inverter, you can set the number of strings to 1 and set the number of modules per string to the total number of modules connected to your inverter.
- If your specific inverter or module is not listed, please [create an issue](https://github.com/Open-HEMS/pvcast/issues) to request support for it. In the meantime you can use a module or inverter that has the same power rating. For example, if you have a 4kW inverter, you can use any 4kW inverter from the list, preferably from the same brand/series. The same goes for modules. It will affect the accuracy of the model somewhat, but it will still work.
