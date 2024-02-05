"""Configuration page for pvcast."""
import dataclasses
import itertools
import logging
import os
from pathlib import Path
from typing import Any, Callable

import polars as pl
import reacton.ipyvuetify as vue
import solara
import yaml
from reacton.core import ValueElement
from solara.lab.toestand import Ref

MAX_LEN_SLIDER = 40

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


def filter_list(*_: Any, input_data: pl.LazyFrame, query: str = "") -> None:
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
) -> ValueElement:
    """Create a row with a slider and a value display."""
    with solara.Row():
        solara.SliderInt(label=label, value=value, min=min_val, max=max_val)
        solara.Info(f"{value.value}" + postfix, dense=True, icon=False)


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
        timeout=3000,
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
    on_delete: Callable[[], None],
    on_close: Callable[[], None],
) -> ValueElement:
    """Take a reactive array and allows editing it.

    Will not modify the original item until 'save' is clicked.
    """
    copy = solara.use_reactive(array.value)

    def save() -> None:
        """Save the edited array."""
        State.on_delete_array(pv_plant.value, array.value)
        State.on_new_array(pv_plant.value, copy.value)
        on_close()

    with solara.Card("Edit", margin=0, style={"justify-content": "space-between"}):
        solara.InputText(
            label="Modify the array name here", value=Ref(copy.fields.name)
        )
        solara.Style(sliders_css)

        # panel tilt
        SliderRow(
            label="Tilt",
            value=Ref(copy.fields.tilt),
            min_val=0,
            max_val=90,
            postfix="°",
        )

        # panel azimuth
        SliderRow(
            label="Azimuth",
            value=Ref(copy.fields.azimuth),
            min_val=0,
            max_val=360,
            postfix="°",
        )

        # modules per string
        SliderRow(
            label="Modules per string",
            value=Ref(copy.fields.modules_per_string),
            min_val=1,
            max_val=20,
        )

        # strings per inverter
        SliderRow(
            label="Strings per inverter",
            value=Ref(copy.fields.strings),
            min_val=1,
            max_val=20,
        )

        # select module
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
    on_delete: Callable[[], None],
    on_close: Callable[[], None],
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
    pv_plant: solara.Reactive[PVPlant], on_delete: Callable[[PVPlant], None]
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
            with solara.Column(style={"width": "100%"}):
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
    on_delete: Callable[[ArrayConfig], None],
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
            with solara.Column(style={"width": "100%"}):
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
def PVPlantNew(on_new: Callable[[PVPlant], None]) -> ValueElement:
    """Component that manages entering new pv_plants.

    This component will create a new PVPlant object, and pass it to the on_new callback.

    :param on_new: callback that will be called with the new PVPlant object.
    :return: a TextField that can be used to enter a new PV plant name.
    """
    new_name, set_new_name = solara.use_state("")
    name_field = vue.TextField(
        v_model=new_name,
        on_v_model=set_new_name,
        label="Enter a new plant name and press enter to add it to the list.",
    )

    def create_new_item(*ignore_args) -> None:
        """Create a new item, and reset the name field."""
        if not new_name:
            return
        new_item = PVPlant(name=new_name)
        on_new(new_item)
        # reset name
        set_new_name("")

    vue.use_event(name_field, "keydown.enter", create_new_item)
    return name_field


@solara.component
def ArrayNew(
    on_new: Callable[[ArrayConfig], None], plant: solara.Reactive[PVPlant]
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
    array_counter: solara.Reactive[int] = solara.reactive(0)

    @staticmethod
    def on_new_plant(plant: PVPlant) -> None:
        """Add a new item to the list of items."""
        for key in State.pv_plants.value:
            if key == plant.name:
                return
        State.pv_plants.set({**State.pv_plants.value, plant.name: plant})

    @staticmethod
    def on_new_array(plant: PVPlant, array: ArrayConfig) -> None:
        """Add a new array to a plant."""
        # update array counter
        State.array_counter.set(State.array_counter.value + 1)
        if array.name == "":
            array = dataclasses.replace(
                array, name=f"Array {State.array_counter.value}"
            )
        plant = dataclasses.replace(plant, arrays=[*plant.arrays, array])
        new_dict = dict(State.pv_plants.value)
        new_dict[plant.name] = plant
        State.pv_plants.set(new_dict)

    @staticmethod
    def on_delete_plant(plant: PVPlant) -> None:
        """Delete a plant from the plant dictionary."""
        try:
            new_dict = dict(State.pv_plants.value)
            new_dict.pop(plant.name)
            State.pv_plants.set(new_dict)
        except KeyError:
            _LOGGER.exception("Plant %s not found in plant list.", plant.name)

    @staticmethod
    def on_delete_array(plant: PVPlant, array: ArrayConfig) -> None:
        """Delete an array from a plant."""
        try:
            new_arrays = list(plant.arrays)
            new_arrays.remove(array)
            plant = dataclasses.replace(plant, arrays=new_arrays)
            new_dict = dict(State.pv_plants.value)
            new_dict[plant.name] = plant
            State.pv_plants.set(new_dict)
        except ValueError:
            pass

    # represent the class content as a dictionary
    @staticmethod
    def as_dict() -> str:
        """Return the class content as a dictionary."""
        plant_dict = {"plant": []}
        for plant in State.pv_plants.value.values():
            plant_dict["plant"].append(dataclasses.asdict(plant))
        return plant_dict


@solara.component
def Page() -> ValueElement:
    """Build the configuration page.

    This page is used to configure the pvcast application.

    It will consist of two columns, one for the active configuration we are editing,
    and one for the current field we are modifying.
    """

    def on_save() -> None:
        """Save the configuration."""
        if not Path.exists(CONFIG_FILE_PATH):
            # create the file if it does not exist
            with Path.open(CONFIG_FILE_PATH, "w+") as file:
                yaml.dump(State.as_dict(), file, default_flow_style=False)

        else:
            # update the file
            config: dict[str, Any] = {}
            with Path.open(CONFIG_FILE_PATH, "r") as file:
                if config := yaml.safe_load(file):
                    config.update(State.as_dict())
                else:
                    config = State.as_dict()
            with Path.open(CONFIG_FILE_PATH, "w+") as file:
                yaml.dump(config, file, default_flow_style=False)

    with solara.Column():
        solara.Title("Plant configuration")
        solara.Info("On this page you can configure your plant(s).")
        with solara.Columns([4, 5]):
            with solara.Column():
                # active configuration
                with solara.Card():
                    solara.Title("Active configuration")
                    solara.Success(
                        f"Number of configured plants: {len(State.pv_plants.value)}"
                    )
                    solara.Markdown("## 🌱 Plants")
                    PVPlantNew(on_new=State.on_new_plant)

                    # save plant config as YAML file
                    solara.Button(
                        "Save configuration",
                        icon_name="mdi-content-save",
                        on_click=on_save,
                        outlined=True,
                        name=True,
                    )

                # list all plants
                if (
                    not State.pv_plants.value
                ):  # the reactive var is never false, but .value can be (when empty)
                    solara.Info(
                        "No plants configured yet. Enter a plant name and hit enter."
                    )
                else:
                    for _, plant_name in enumerate(State.pv_plants.value):
                        pv_plant = Ref(State.pv_plants.fields[plant_name])
                        PVPlantListItem(pv_plant, on_delete=State.on_delete_plant)

            # field we are currently editing
            with solara.Card():
                solara.Title("Current field")
                solara.Info("This is the current field.")
                solara.Button("Edit")
