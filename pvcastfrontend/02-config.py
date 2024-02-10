"""Configuration page for pvcast."""
import dataclasses
import itertools
import logging
import math
import os
import typing
from pathlib import Path

import ipyleaflet as leaf
import polars as pl
import reacton.ipyvuetify as vue
import solara
import solara.lab

# from voluptuous import vol.Coerce, vol.Coerce, IsTrue, vol.Range, vol.Required, vol.Schema
import voluptuous as vol
import voluptuous.error
import yaml
from reacton.core import ValueElement
from solara.lab.toestand import Ref

MAX_LEN_SLIDER = 40
SNACKBACK_TIMEOUT = 6000

# set the logging format
LOG_FORMAT = "%(asctime)s [%(levelname)8s] %(message)s (%(name)s:%(lineno)s)"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.ERROR, format=LOG_FORMAT, datefmt=DATE_FORMAT, force=True
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


"""
# create a flexible PV plant configuration system, following the config system of pvcast:
-----------------------
# PV system configuration
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
  - name: South
"""

BASE_PATH = Path(__file__).parent

# CSS
sliders_css = BASE_PATH / ".data/CSS/sliders.css"

# config.yaml file path
CONFIG_FILE_PATH = os.environ.get("CONFIG_FILE_PATH", BASE_PATH / ".data/config.yaml")

# component parameter paths
COMPONENT_PATH = os.environ.get("COMPONENT_PATH", BASE_PATH / ".data/proc")
mod_param: pl.LazyFrame = pl.scan_csv(COMPONENT_PATH / "cec_modules.csv")
inv_param: pl.LazyFrame = pl.scan_csv(COMPONENT_PATH / "cec_inverters.csv")

# how-to markdown
how_to_path = BASE_PATH / ".data/howto.md"


def load_howto() -> str:
    """Load the how-to markdown file."""
    with Path.open(how_to_path) as file:
        return file.read()


how_to = load_howto()

# update proxy for triggering a refresh
update_proxy = solara.reactive(0)


def update_proxy_callback() -> None:
    """Update the proxy."""
    update_proxy.set(update_proxy.value + 1)


@dataclasses.dataclass(frozen=True)
class ArrayConfig:
    """Array configuration item."""

    name: str = ""
    tilt: int = 30
    azimuth: int = 180
    modules_per_string: int = 1
    strings: int = 1
    module: str = ""


@dataclasses.dataclass(frozen=True)
class PVPlant:
    """PV plant top level configuration item."""

    name: str
    inverter: str = ""
    microinverter: bool = False
    arrays: list[ArrayConfig] = dataclasses.field(default_factory=list)


def generate_regex_pattern(input_string: str) -> str:
    """Generate a regex pattern from a string.

    A string could be "Yes no maybe" and the pattern would become:
    ((yes).*(no).*(maybe))|((yes).*(maybe).*(no))|((no).*(yes).*(maybe))|... etc

    :param input_string: the input string to generate the pattern from
    :return: the generated pattern as a string
    """
    words = input_string.split()
    words = filter(lambda x: len(x) > 0, words)
    word_permutations = itertools.permutations(words)
    patterns = []

    for perm in word_permutations:
        pattern_part = ".*".join(f"(?i)({word})" for word in perm)
        patterns.append(f"({pattern_part})")

    return "|".join(patterns)


def filter_list(*_: typing.Any, input_data: pl.LazyFrame, query: str = "") -> None:
    """Filter the list for the given query.

    :param input_data: the input data to filter
    :param query: the query to filter the data with
    :return: a list of items that match the query
    """
    try:
        if len(query) == 0:
            return input_data.select(pl.col("index")).collect().to_series().to_list()
        return (
            input_data.filter(
                pl.col("index").str.contains(generate_regex_pattern(query))
            )
            .select(pl.col("index"))
            .collect()
            .to_series()
            .to_list()
        )
    except pl.ComputeError as exc:
        solara.Error(f"Error: {exc}")
        return []


@solara.component
def SliderRow(
    label: str,
    value: solara.Reactive[int],
    min_val: int,
    max_val: int,
    postfix: str = "",
    **kwargs: typing.Any,
) -> ValueElement:
    """Create a row with a slider and a value display."""
    with solara.Row():
        solara.SliderInt(label=label, value=value, min=min_val, max=max_val, **kwargs)
        solara.Info(f"{value.value}" + postfix, dense=True, icon=False)


@solara.component
def InputIntRow(
    label: str,
    value: solara.Reactive[int],
    upper_bound: int = math.inf,
    lower_bound: int = 0,
) -> ValueElement:
    """Create a row with an input field for integers."""
    with solara.Row():

        def filter_value(*args: str) -> None:
            """Filter the input field."""
            val = max(int(args[-1]), lower_bound)
            val = min(val, upper_bound)
            value.set(val)

        solara.InputInt(label=label, value=value, on_value=filter_value)
        button_style = {
            "height": "30px",
            "width": "25px",
            "margin-top": "15px",
            "margin-bottom": "0px",
        }

        # plus 1 button
        solara.Button(
            icon_name="mdi-plus",
            on_click=lambda: value.set(value.value + 1),
            style=button_style,
            color="green",
            outlined=True,
        )

        # minus 1 button
        solara.Button(
            icon_name="mdi-minus",
            on_click=lambda: value.set(value.value - 1),
            style=button_style,
            color="red",
            outlined=True,
        )


@solara.component
def PVComponentSelect(
    copy: solara.Reactive[dataclasses.dataclass],
    component_list: pl.LazyFrame,
    field: str,
) -> ValueElement:
    """Select a PV component from a given list."""
    filter_v, set_filter = solara.use_state("")
    found_components, set_components = solara.use_state([])

    def input_hook(*args: str) -> None:
        """Input field hook."""
        query = args[-1]
        set_components(filter_list(input_data=component_list, query=query))

    # create the autocomplete component to select the component
    component = vue.Autocomplete(
        label=f"Start typing to filter {field}s by name",
        filled=True,
        v_model=filter_v,
        items=found_components,
        on_v_model=set_filter,
        style={"width": "100%"},
        dense=False,
        clearable=True,
        no_filter=True,
        auto_select_first=True,
        loading=len(found_components) == 0,
        no_data_text=f"No matching {field}s found",
    )
    vue.use_event(component, "update:search-input", input_hook)

    # snackbar message
    snack = vue.Snackbar(
        v_model=filter_v,
        timeout=SNACKBACK_TIMEOUT,
        color="success",
        children=[f"Selected {field}: {copy.value.__getattribute__(field)}"],
    )
    solara.display(snack)

    # write the selected module to the array
    if filter_v:
        copy.value = dataclasses.replace(copy.value, **{field: filter_v})

    solara.Success(
        f"Selected {field}: {copy.value.__getattribute__(field)}"
    ) if copy.value.__getattribute__(field) else solara.Warning(
        f"No {field} selected yet."
    )


@solara.component
def ArrayEdit(
    pv_plant: solara.Reactive[PVPlant],
    array: solara.Reactive[ArrayConfig],
    on_delete: typing.Callable[[], None],
    on_close: typing.Callable[[], None],
) -> ValueElement:
    """Take a reactive array and allows editing it.

    Will not modify the original item until 'save' is clicked.
    """
    copy = solara.use_reactive(array.value)

    def save() -> None:
        """Save the edited array."""
        pv_plant.value.arrays[pv_plant.value.arrays.index(array.value)] = copy.value
        _LOGGER.debug("Saving the array via edit button: %s", copy.value)

        # update the proxy to trigger a refresh
        update_proxy_callback()
        on_close()

    with solara.Card("Edit", margin=0, style={"justify-content": "space-between"}):
        solara.InputText(
            label="Modify the array name here", value=Ref(copy.fields.name)
        )
        solara.Style(sliders_css)

        # modules per string and strings per inverter
        padding_top = {"padding-top": "16px", "padding-bottom": "16px"}
        with solara.Column(style=padding_top):
            # panel tilt
            InputIntRow(
                label="Tilt in degrees from horizontal",
                value=Ref(copy.fields.tilt),
                upper_bound=90,
            )

            # panel azimuth
            InputIntRow(
                label="Azimuth in degrees clockwise from North",
                value=Ref(copy.fields.azimuth),
                upper_bound=360,
            )

            # modules per string
            InputIntRow(
                label="Modules per string (inverter input)",
                value=Ref(copy.fields.modules_per_string),
                lower_bound=1,
            )

            # number of strings
            InputIntRow(
                label="Number of strings connected to the inverter",
                value=Ref(copy.fields.strings),
                lower_bound=1,
            )

        # module selector for the array
        PVComponentSelect(copy, mod_param, "module")

        with solara.CardActions():
            vue.Spacer()
            solara.Button(
                "Save",
                icon_name="mdi-content-save",
                on_click=save,
                outlined=True,
                name=True,
            )
            solara.Button(
                "Close",
                icon_name="mdi-window-close",
                on_click=on_close,
                outlined=True,
                name=True,
            )
            solara.Button(
                "Delete",
                icon_name="mdi-delete",
                on_click=on_delete,
                outlined=True,
                name=True,
            )


@solara.component
def PVPlantEdit(
    pv_plant: solara.Reactive[PVPlant],
    on_delete: typing.Callable[[], None],
    on_close: typing.Callable[[], None],
) -> ValueElement:
    """Take a reactive pv_plant and allows editing it.

    Will not modify the original item until 'save' is clicked.
    """
    copy = solara.use_reactive(pv_plant.value)

    def save() -> None:
        """Save the edited pv_plant."""
        State.on_delete_plant(pv_plant.value)
        State.on_new_plant(copy.value)
        on_close()

    with solara.Card("Edit", margin=0, style={"justify-content": "space-between"}):
        solara.InputText(
            label="Modify the plant name here", value=Ref(copy.fields.name)
        )

        # select inverter
        PVComponentSelect(copy, inv_param, "inverter")

        # microinverter switch
        solara.Checkbox(
            label="Toggle if inverter is a microinverter",
            value=Ref(copy.fields.microinverter),
        )
        solara.Info(
            "A microinverter is a small inverter that is typically attached at each solar panel, "
            "with each panel having its own inverter. This is in contrast to a string inverter, "
            "which is connected to multiple panels. Example of microinverters are Enphase IQ series.",
            dense=True,
        )

        with solara.CardActions():
            vue.Spacer()
            solara.Button(
                "Save",
                icon_name="mdi-content-save",
                on_click=save,
                outlined=True,
                name=True,
            )
            solara.Button(
                "Close",
                icon_name="mdi-window-close",
                on_click=on_close,
                outlined=True,
                name=True,
            )
            solara.Button(
                "Delete",
                icon_name="mdi-delete",
                on_click=on_delete,
                outlined=True,
                name=True,
            )


@solara.component
def PVPlantListItem(
    pv_plant: solara.Reactive[PVPlant], on_delete: typing.Callable[[PVPlant], None]
) -> ValueElement:
    """Display a single PV plant item, modifications are done 'in place'.

    For demonstration purposes, we allow editing the item in a dialog as well.
    This will not modify the original item until 'save' is clicked.
    """
    # edit button
    edit, set_edit = solara.use_state(initial=False)

    # card
    with solara.Card(f"🌻 {pv_plant.value.name}"):
        with solara.v.ListItem():
            with solara.Column(style={"width": "100%", "margin": "auto"}):
                with solara.Row():
                    solara.Button(
                        "EDIT PLANT",
                        icon_name="mdi-pencil",
                        on_click=lambda: set_edit(True),
                        style={"flex-grow": "1"},
                    )
                    solara.Button(
                        "DELETE PLANT",
                        icon_name="mdi-delete",
                        on_click=lambda: on_delete(pv_plant.value),
                        style={"flex-grow": "1"},
                    )

                # list all arrays for this plant
                if pv_plant.value.arrays:
                    for index in range(len(pv_plant.value.arrays)):
                        array = Ref(pv_plant.fields.arrays[index])
                        ArrayListItem(pv_plant, array, on_delete=State.on_delete_array)
                ArrayNew(on_new=State.on_new_array, plant=pv_plant)

            with vue.Dialog(
                v_model=edit, persistent=True, max_width="500px", on_v_model=set_edit
            ):
                if edit:

                    def on_delete_in_edit() -> None:
                        """Delete the item, and close the dialog."""
                        on_delete(pv_plant.value)
                        set_edit(False)

                    PVPlantEdit(
                        pv_plant,
                        on_delete=on_delete_in_edit,
                        on_close=lambda: set_edit(False),
                    )


@solara.component
def ArrayListItem(
    pv_plant: solara.Reactive[PVPlant],
    array: solara.Reactive[ArrayConfig],
    on_delete: typing.Callable[[ArrayConfig], None],
) -> ValueElement:
    """Display a single array item, modifications are done 'in place'.

    For demonstration purposes, we allow editing the item in a dialog as well.
    This will not modify the original item until 'save' is clicked.
    """
    # edit button
    edit, set_edit = solara.use_state(initial=False)

    with solara.Card(
        f"⚡ {array.value.name}", margin=0, style={"backgroud-color": "green"}
    ):
        with solara.v.ListItem():
            with solara.Column(style={"width": "100%", "margin": "auto"}):
                with solara.Row():
                    solara.Button(
                        "EDIT ARRAY",
                        icon_name="mdi-pencil",
                        on_click=lambda: set_edit(True),
                        style={"flex-grow": "1", "width": "50%"},
                        color="primary",
                    )
                    solara.Button(
                        "DELETE ARRAY",
                        icon_name="mdi-delete",
                        on_click=lambda: on_delete(pv_plant.value, array.value),
                        style={"flex-grow": "1", "width": "50%"},
                        color="primary",
                    )
            with vue.Dialog(
                v_model=edit, persistent=True, max_width="500px", on_v_model=set_edit
            ):
                if edit:

                    def on_delete_in_edit() -> None:
                        """Delete the item, and close the dialog."""
                        on_delete(pv_plant.value, array.value)
                        set_edit(False)

                    ArrayEdit(
                        pv_plant,
                        array,
                        on_delete=on_delete_in_edit,
                        on_close=lambda: set_edit(False),
                    )


@solara.component
def PVPlantNew(on_new: typing.Callable[[PVPlant], None]) -> ValueElement:
    """Component that manages entering new pv_plants.

    This component will create a new PVPlant object, and pass it to the on_new callback.

    :param on_new: callback that will be called with the new PVPlant object.
    :return: a TextField that can be used to enter a new PV plant name.
    """
    new_name, set_new_name = solara.use_state("")
    name_field = vue.TextField(
        v_model=new_name,
        on_v_model=set_new_name,
        label="Enter a new plant name and press enter to start or press 'LOAD CONFIG' below.",
    )

    def create_new_item(*ignore_args) -> None:
        """Create a new item, and reset the name enter field."""
        if not new_name:
            return
        new_item = PVPlant(name=new_name)
        on_new(new_item)
        # reset name enter field
        set_new_name("")

    vue.use_event(name_field, "keydown.enter", create_new_item)
    return name_field


@solara.component
def ArrayNew(
    on_new: typing.Callable[[ArrayConfig], None], plant: solara.Reactive[PVPlant]
) -> ValueElement:
    """Component that manages entering new arrays."""
    solara.Button(
        "ADD ARRAY",
        icon_name="mdi-plus",
        color="primary",
        on_click=lambda: on_new(plant.value, ArrayConfig()),
        style={"flex-grow": "1", "width": "100%"},
    )


class State:
    """State for the pvcast configuration page."""

    pv_plants: solara.Reactive[dict[str, PVPlant]] = solara.reactive({})
    array_count = solara.reactive(0)

    @staticmethod
    def on_new_plant(plant: PVPlant) -> None:
        """Add a new item to the list of items."""
        _LOGGER.debug("Adding plant %s to the list.", plant.name)
        for key in State.pv_plants.value:
            if key == plant.name:
                _LOGGER.debug("Plant %s already exists.", plant.name)
                return
        State.pv_plants.set({**State.pv_plants.value, plant.name: plant})

    @staticmethod
    def on_new_array(plant: PVPlant, array: ArrayConfig) -> None:
        """Add a new array to a plant."""
        _LOGGER.debug("on_new_array start: %s to plant %s.", array.name, plant.name)
        State.array_count.set(State.array_count.value + 1)

        # if the array name is empty, generate a new name
        if array.name == "":
            _LOGGER.debug("Array name is empty, generating a new name.")
            array = dataclasses.replace(array, name=f"Array {State.array_count.value}")
        _LOGGER.debug("on_new_array middle: %s to plant %s.", array.name, plant.name)

        # add the new array to the plant
        plant = dataclasses.replace(plant, arrays=[*plant.arrays, array])

        # update the plant in the dictionary
        new_dict = dict(State.pv_plants.value)
        new_dict[plant.name] = plant
        State.pv_plants.set(new_dict)

    @staticmethod
    def on_delete_plant(plant: PVPlant) -> None:
        """Delete a plant from the plant dictionary."""
        _LOGGER.debug("Deleting plant %s from the list.", plant.name)
        try:
            new_dict = dict(State.pv_plants.value)
            new_dict.pop(plant.name)
            State.pv_plants.set(new_dict)
        except KeyError:
            _LOGGER.exception("Plant %s not found in plant list.", plant.name)

    @staticmethod
    def on_delete_array(plant: PVPlant, array: ArrayConfig) -> None:
        """Delete an array from a plant."""
        _LOGGER.debug("Deleting array %s from plant %s.", array.name, plant.name)
        try:
            new_arrays = list(plant.arrays)
            new_arrays.remove(array)
            plant = dataclasses.replace(plant, arrays=new_arrays)
            new_dict = dict(State.pv_plants.value)
            new_dict[plant.name] = plant
            State.pv_plants.set(new_dict)
        except ValueError:
            _LOGGER.warning(
                "Deleting array %s but not found in plant %s.", array.name, plant.name
            )

    @staticmethod
    def config_schema() -> vol.Schema:
        """Get the configuration schema as a vol.Schema object.

        :return: Config schema.
        """
        _LOGGER.debug("Generating configuration schema.")
        return vol.Schema(
            {
                vol.Required("plant"): vol.All(
                    [
                        {
                            vol.Required("name"): str,
                            vol.Required("inverter"): str,
                            vol.Required("microinverter"): vol.Coerce(bool),
                            vol.Required("arrays"): [
                                {
                                    vol.Required("name"): str,
                                    vol.Required("tilt"): vol.All(
                                        vol.Coerce(float), vol.Range(min=0, max=90)
                                    ),
                                    vol.Required("azimuth"): vol.All(
                                        vol.Coerce(float), vol.Range(min=0, max=360)
                                    ),
                                    vol.Required("modules_per_string"): vol.All(
                                        int, vol.Range(min=1)
                                    ),
                                    vol.Required("strings"): vol.All(
                                        int, vol.Range(min=1)
                                    ),
                                    vol.Required("module"): str,
                                }
                            ],
                        }
                    ],
                    vol.Length(min=1),
                )
            }
        )

    # represent the class content as a dictionary
    @staticmethod
    def as_dict() -> dict[str, typing.Any]:
        """Return the class content as a dictionary."""
        plant_dict = {"plant": []}
        for plant in State.pv_plants.value.values():
            plant_dict["plant"].append(dataclasses.asdict(plant))
        return plant_dict


@solara.component
def PlantConfiguration() -> ValueElement:  # noqa: PLR0915
    """Build the configuration page."""
    file_missing, set_file_missing = solara.use_state(initial=False)
    save_success, set_save_success = solara.use_state(initial=False)
    save_error, set_save_error = solara.use_state(initial=False)
    err_message, set_err_message = solara.use_state("")

    def on_save() -> None:
        """Save the configuration."""
        config_final: dict[str, typing.Any] = {}
        config_state: dict[str, typing.Any] = State.as_dict()

        # if the current config is empty we won't save it but show an error
        if len(config_state["plant"]) == 0:
            set_save_error(True)
            set_err_message("No plants configured yet.")
            _LOGGER.warning("Tried to save an empty configuration.")
            return

        # validate the configuration
        try:
            State.config_schema()(config_state)
        except (voluptuous.error.Invalid, voluptuous.error.MultipleInvalid) as exc:
            set_save_error(True)
            set_err_message(f"The configuration is invalid: {exc}")
            _LOGGER.error(  # noqa: TRY400
                "Error saving configuration, configuration is invalid: %s", exc
            )
            return

        # if config.yaml is present and not empty, update config_final with its content
        if Path.exists(CONFIG_FILE_PATH):
            config_final = yaml.safe_load(Path.open(CONFIG_FILE_PATH, "r"))

        # update config_final with the current state
        with Path.open(CONFIG_FILE_PATH, "w+") as file:
            config_final.update(config_state)
            yaml.dump(config_final, file, default_flow_style=False, sort_keys=False)

        # generate a snack bar message
        set_save_success(True)
        _LOGGER.info("Configuration saved successfully to %s.", CONFIG_FILE_PATH)

    def on_load() -> None:
        """Load the configuration."""
        set_file_missing(False)

        if Path.exists(CONFIG_FILE_PATH):
            with Path.open(CONFIG_FILE_PATH, "r") as file:
                config = yaml.safe_load(file)
                State.pv_plants.set(
                    {
                        plant["name"]: PVPlant(
                            name=plant["name"],
                            inverter=plant["inverter"],
                            microinverter=plant["microinverter"],
                            arrays=[ArrayConfig(**array) for array in plant["arrays"]],
                        )
                        for plant in config["plant"]
                    }
                )
        else:
            set_file_missing(True)

    # active configuration
    with solara.Card(style={"margin": "auto"}):
        solara.Title("Active configuration")
        solara.Success(f"Number of configured plants: {len(State.pv_plants.value)}")
        solara.Markdown("## 🌱 Plants")
        PVPlantNew(on_new=State.on_new_plant)

        # save plant config as YAML file
        with solara.Row(style={"width": "100%", "margin": "auto"}):
            solara.Button(
                "Save config",
                icon_name="mdi-content-save",
                on_click=on_save,
                outlined=True,
                name=True,
                style={"flex-grow": "1"},
            )

            # load plant config from YAML file
            solara.Button(
                "Load config",
                icon_name="mdi-file-upload",
                on_click=on_load,
                outlined=True,
                name=True,
                style={"flex-grow": "1"},
            )

        # show a snack bar if the file does not exist
        snack_file = vue.Snackbar(
            v_model=file_missing,
            timeout=SNACKBACK_TIMEOUT,
            color="error",
            children=[f"No configuration file found at {CONFIG_FILE_PATH}."],
            on_v_model=set_file_missing,
        )
        solara.display(snack_file)

        # show a snack bar if the file was saved successfully
        snack_save = vue.Snackbar(
            v_model=save_success,
            timeout=SNACKBACK_TIMEOUT,
            color="success",
            children=[f"Configuration saved successfully to {CONFIG_FILE_PATH}."],
            on_v_model=set_save_success,
        )
        solara.display(snack_save)

        # show a snack bar if the file couldn't be saved
        snack_error = vue.Snackbar(
            v_model=save_error,
            timeout=SNACKBACK_TIMEOUT,
            color="error",
            children=[
                f"Error saving configuration to {CONFIG_FILE_PATH}. Reason: {err_message}"
            ],
            on_v_model=set_save_error,
        )
        solara.display(snack_error)

    # list all plants
    if (
        not State.pv_plants.value
    ):  # the reactive var is never false, but .value can be (when empty)
        solara.Info("No plants configured yet. Enter a plant name and hit enter.")
    else:
        for _, plant_name in enumerate(State.pv_plants.value):
            pv_plant = Ref(State.pv_plants.fields[plant_name])
            PVPlantListItem(pv_plant, on_delete=State.on_delete_plant)


@solara.component
def PlantConfigurationValidator() -> ValueElement:
    """Validate the configuration."""
    # read the proxy to trigger a refresh
    _ = update_proxy.get()
    config_state = State.as_dict()

    with solara.Card(style={"overflow-y": "scroll", "height": "750px"}):
        if len(config_state["plant"]) == 0:
            solara.Warning("No plants configured yet.")
            return
        try:
            State.config_schema()(config_state)
            solara.Success("The configuration is valid.")
            yaml_config = yaml.dump(
                config_state, default_flow_style=False, sort_keys=False
            )
            solara.HTML(tag="div", unsafe_innerHTML=f"<pre>{yaml_config}</pre>")
        except (voluptuous.error.Invalid, voluptuous.error.MultipleInvalid) as exc:
            solara.Error(f"The configuration is invalid: {exc}")


@solara.component
def PlantConfigurationHowto() -> ValueElement:
    """Display the how-to markdown."""
    with solara.Card(style={"overflow-y": "scroll", "height": "750px"}):
        solara.Markdown(how_to)


class Compass(leaf.Marker):
    """Compass is a composite marker."""

    def __init__(
        self, lf_map: leaf.Map, radius: int = 20, azimuth: solara.Reactive[int] = 0
    ) -> None:
        """Create a compass marker."""
        icon = leaf.AwesomeIcon(name="fa-bolt", marker_color="red", icon_color="black")
        super().__init__(
            location=lf_map.center,
            draggable=True,
            on_move=self._update_location,
            icon=icon,
        )
        self._zoom_default = 20
        self._center_default = (lf_map.center[0], lf_map.center[1])
        self.m_to_lat = lambda meters: meters / 110_574
        self.radius = radius
        self.azimuth = azimuth

        # reactive variables
        self._center: solara.Reactive[typing.Tuple[float, float]] = solara.use_reactive(
            self._center_default
        )
        self._zoom = solara.use_reactive(self._zoom_default)

        # composite markers
        self._circle = leaf.Circle(
            location=self._center.value,
            radius=radius,
            color="black",
            fill_color="blue",
            fill_opacity=0.1,
        )

        self._north_line = leaf.Polyline(
            locations=[
                (self._center.value[0], self._center.value[1]),
                (
                    self._center.value[0] + 0.95 * self.m_to_lat(radius),
                    self._center.value[1],
                ),
            ],
            color="black",
            fill=False,
        )

        # center circle marker
        self._center_circle = leaf.CircleMarker(
            location=self._center.value,
            radius=5,
            color="black",
            fill_color="red",
            fill_opacity=1,
        )

        # azimuth angle indicator polyline
        self.azimuth_line = leaf.Polyline(
            locations=[
                (self._center.value[0], self._center.value[1]),
                self.calc_new_latlon(*self._center.value, 90),
            ],
            color="green",
            fill=False,
        )

        # link movements
        super().observe(self._update_location, "location")

        # group so we can name and deselect all markers simultaneously
        self.layer_group = leaf.LayerGroup(
            layers=(
                self._circle,
                self._north_line,
                self,
                self.azimuth_line,
                self._center_circle,
            ),
            name="Compass",
        )

    def _update_location(self, *_: typing.Any) -> None:
        """Update the location."""
        self._circle.location = super().location
        self._center_circle.location = super().location
        self._north_line.locations = [
            super().location,
            (super().location[0] + self.m_to_lat(self.radius), super().location[1]),
        ]

        # calculate distances
        self.azimuth_line.locations = [
            super().location,
            self.calc_new_latlon(*super().location, self.azimuth.value),
        ]

    def calc_new_latlon(
        self, lat: float, lon: float, angle_deg: float
    ) -> tuple[float, float]:
        """Calculate new latitude and longitude based on a rotation angle."""
        # clockwise rotation correction
        angle_deg = -1 * angle_deg

        # distance in meters from the center for x and y
        dist_y = 1.5 * self.radius * math.cos(math.radians(angle_deg))
        dist_x = 1.5 * self.radius * math.sin(math.radians(angle_deg)) * 1.05

        # radius of the earth in meters
        xi = 6378137

        # new latitude and longitude taking into account the earth's curvature
        new_lat = lat + (180 / math.pi) * (dist_y / xi)
        new_lon = lon + (180 / math.pi) * (dist_x / xi) / math.cos(lat)
        return new_lat, new_lon


@solara.component
def PlantConfigurationAzimuth() -> ValueElement:
    """Display compass for help in determining the PV array azimuth.

    Icon attribution:
    <a href="https://www.flaticon.com/free-icons/close" title="close icons">Close icons created by Darius Dan - Flaticon</a>
    """
    info_html = """
<pre><p style="font-family: Arial">Use the compass to find the correct azimuth.

1. Find your location and zoom in.
2. Orient the compass so that it aligns with your panels.
3. Read the azimuth angle from the compass.
4. Enter the azimuth angle in the configuration.</p></pre>
"""
    solara.Info(children=[solara.HTML(tag="div", unsafe_innerHTML=info_html)])

    # default values
    latitude = float(os.environ.get("LATITUDE", 51.0))
    longitude = float(os.environ.get("LONGITUDE", 3.0))
    zoom_default = 20
    center_default = (latitude, longitude)

    # reactive variables
    center = solara.use_reactive(center_default)
    zoom = solara.use_reactive(zoom_default)
    azimuth_angle = solara.use_reactive(90)

    # add basemaps
    maps = {
        "WorldImagery": leaf.basemaps.Esri.WorldImagery,
    }

    # define the map
    lf_map = leaf.Map(
        zoom=zoom.value,
        center=center.value,
        scroll_wheel_zoom=True,
        basemap=leaf.basemaps.OpenStreetMap.Mapnik,
    )

    # add basemaps
    for name, basemap in maps.items():
        tile_map = leaf.basemap_to_tiles(basemap)
        tile_map.name = name
        tile_map.base = True
        lf_map.add_layer(tile_map)

    # add controls
    lf_map.add_control(leaf.FullScreenControl())
    lf_map.add_control(leaf.LayersControl())
    lf_map.attribution_control = False

    # create compass
    compass = Compass(lf_map, azimuth=azimuth_angle)
    lf_map.add_layer(compass.layer_group)

    # update the angle of the azimuth line when the slider changes
    def update_line_angle(*_: typing.Any) -> None:
        """Update the azimuth line."""
        compass.azimuth_line.locations = [
            compass.location,
            compass.calc_new_latlon(*compass.location, azimuth_angle.value),
        ]

    # add azimuth angle slider
    solara.Style(sliders_css)
    SliderRow(
        label="Azimuth",
        value=azimuth_angle,
        min_val=0,
        max_val=360,
        postfix="°",
        on_value=update_line_angle,
    )

    # Isolation is required to prevent the map from overlapping navigation (when screen width < 960px)
    with solara.Column(style={"isolation": "isolate", "height": "400px"}):
        solara.display(lf_map)


@solara.component
def PlantConfigurationHelpers() -> ValueElement:
    """Build the configuration page."""
    with solara.Card(style={"margin": "auto"}):
        with solara.lab.Tabs():
            # design help
            with solara.lab.Tab(icon_name="mdi-help", label="How-to"):
                PlantConfigurationHowto()

            # configuration validator
            with solara.lab.Tab(icon_name="mdi-check", label="Config Validator"):
                PlantConfigurationValidator()

            # OSM compass for selecting the azimuth
            with solara.lab.Tab(icon_name="mdi-compass", label="OSM Compass"):
                PlantConfigurationAzimuth()


@solara.component
def Page() -> ValueElement:
    """Build the configuration page.

    This page is used to configure the pvcast application.

    It will consist of two columns, one for the active configuration we are editing,
    and one for the current field we are modifying.
    """
    with solara.Column():
        solara.Info("On this page you can configure your plant(s).")
        with solara.Columns([4, 5]):
            # configuration editor
            with solara.Column():
                PlantConfiguration()

            # configuration helpers
            with solara.Column():
                PlantConfigurationHelpers()
