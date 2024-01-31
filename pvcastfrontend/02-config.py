"""Configuration page for pvcast."""
import dataclasses
from typing import Callable

import reacton.ipyvuetify as vue
import solara
from reacton.core import ValueElement
from solara.lab.toestand import Ref

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


@dataclasses.dataclass
class ArrayConfig:
    """Array configuration item."""

    name: str
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


@solara.component
def PVPlantEdit(
    pv_plant: solara.Reactive[PVPlant],
    on_delete: Callable[[], None],
    on_close: Callable[[], None],
) -> ValueElement:
    """Take a reactive pvplant and allows editing it.

    Will not modify the original item until 'save' is clicked.
    """
    copy = solara.use_reactive(pv_plant.value)

    def save() -> None:
        """Save the edited pvplant."""
        pv_plant.set(copy.value)
        on_close()

    with solara.Card("Edit", margin=0):
        solara.InputText(label="", value=Ref(copy.fields.name))
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
    pvplant: solara.Reactive[PVPlant], on_delete: Callable[[PVPlant], None]
) -> ValueElement:
    """Display a single PV plant item, modifications are done 'in place'.

    For demonstration purposes, we allow editing the item in a dialog as well.
    This will not modify the original item until 'save' is clicked.
    """
    # edit button
    edit, set_edit = solara.use_state(initial=False)

    # card
    with solara.Card(f"🌻 PV plant: {pvplant.value.name}"):
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
                        on_click=lambda: on_delete(pvplant.value),
                        style={"flex-grow": "1"},
                    )
                with solara.Card(f"☀️ PV arrays for: {pvplant.value.name}"):
                    solara.Button(
                        "ADD ARRAY",
                        icon_name="mdi-plus",
                        color="primary",
                        on_click=lambda: pvplant.value.arrays.append(
                            ArrayConfig(name="New array")
                        ),
                    )

            with vue.Dialog(
                v_model=edit, persistent=True, max_width="500px", on_v_model=set_edit
            ):
                if edit:

                    def on_delete_in_edit() -> None:
                        """Delete the item, and close the dialog."""
                        on_delete(pvplant.value)
                        set_edit(False)

                    PVPlantEdit(
                        pvplant,
                        on_delete=on_delete_in_edit,
                        on_close=lambda: set_edit(False),
                    )



@solara.component
def ArrayListItem(
    array: solara.Reactive[ArrayConfig], on_delete: Callable[[ArrayConfig], None]
) -> ValueElement:
    """Display a single array item, modifications are done 'in place'.

    For demonstration purposes, we allow editing the item in a dialog as well.
    This will not modify the original item until 'save' is clicked.
    """
    edit, set_edit = solara.use_state(initial=False)
    with vue.ListItem():
        solara.Button(
            icon_name="mdi-delete", icon=True, on_click=lambda: on_delete(array.value)
        )
        solara.Button(
            icon_name="mdi-pencil", icon=True, on_click=lambda: set_edit(True)
        )
        with vue.Dialog(
            v_model=edit, persistent=True, max_width="500px", on_v_model=set_edit
        ):
            if edit:

                def on_delete_in_edit() -> None:
                    """Delete the item, and close the dialog."""
                    on_delete(array.value)
                    set_edit(False)

                ArrayEdit(
                    array, on_delete=on_delete_in_edit, on_close=lambda: set_edit(False)
                )


@solara.component
def ArrayEdit(
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
        array.set(copy.value)
        on_close()

    with solara.Card("Edit", margin=0):
        solara.InputText(label="", value=Ref(copy.fields.name))
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
def PVPlantNew(on_new_plant: Callable[[PVPlant], None]) -> ValueElement:
    """Component that manages entering new pvplants."""
    new_name, set_new_name = solara.use_state("")
    name_field = vue.TextField(
        v_model=new_name, on_v_model=set_new_name, label="Enter a new PV plant name"
    )

    def create_new_item(*ignore_args) -> None:
        """Create a new item, and reset the name field."""
        if not new_name:
            return
        new_item = PVPlant(name=new_name)
        on_new_plant(new_item)
        # reset name
        set_new_name("")

    vue.use_event(name_field, "keydown.enter", create_new_item)
    return name_field

@solara.component
def ArrayNew(on_new_array: Callable[[ArrayConfig], None]) -> ValueElement:
    """Component that manages entering new arrays."""

    def create_new_item(*ignore_args) -> None:
        """Create a new item, and reset fields."""





class State:
    """State for the pvcast configuration page."""

    pvplants: solara.Reactive[dict[PVPlant]] = solara.reactive({})

    @staticmethod
    def on_new_plant(plant: PVPlant) -> None:
        """Add a new item to the list of items."""
        for key in State.pvplants.value:
            # name must be unique
            if key == plant.name:
                return

        # add new item
        State.pvplants.value = {plant.name: plant, **State.pvplants.value}

    @staticmethod
    def on_new_array(plant: PVPlant, array: ArrayConfig) -> None:
        """Add a new array to a plant."""



    @staticmethod
    def on_delete(item: PVPlant) -> None:
        """Delete an item from the list of items."""
        new_items = list(State.pvplants.value)
        new_items.remove(item)
        State.pvplants.value = new_items


@solara.component
def Page() -> ValueElement:
    """Build the configuration page.

    This page is used to configure the pvcast application.

    It will consist of two columns, one for the active configuration we are editing,
    and one for the current field we are modifying.
    """
    with solara.Column():
        solara.Title("Plant configuration")
        solara.Info("On this page you can configure your PV plant(s).")
        with solara.Columns([2, 3]):
            # active configuration
            with solara.Card():
                solara.Title("Active configuration")
                solara.Success(
                    f"Number of configured PV plants: {len(State.pvplants.value)}"
                )
                solara.Markdown("## 🌱 PV plants")
                PVPlantNew(on_new_plant=State.on_new_plant)
                if State.pvplants.value:
                    # make plant attribute a reactive variable
                    for plant_name in State.pvplants.value:
                        pv_plant = Ref(State.pvplants.fields[plant_name])
                        PVPlantListItem(pv_plant, on_delete=State.on_delete)

                else:
                    solara.Info(
                        "No PV plants configured yet. Enter a PV plant name and hit enter."
                    )

            # field we are currently editing
            with solara.Card():
                solara.Title("Current field")
                solara.Info("This is the current field.")
                solara.Button("Edit")
