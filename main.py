"""A CAD and 3D printing project planner."""
from drafter import add_website_css
from dataclasses import dataclass
from math import isfinite
import sys

from drafter import (
    Page, route, start_server, set_site_information,
    Header, TextBox, TextArea, SelectBox, Button, Link,
    Aside, Nav, Main, Div, Paragraph, Label
)


@dataclass
class Project:
    """Information about one part."""
    name: str
    length: float
    width: float
    height: float
    material: str
    hours: float
    status: str
    notes: str


@dataclass
class State:
    """Information shared between the website's pages."""
    projects: list[Project]
    printer_length: float
    printer_width: float
    printer_height: float
    status_filter: str
    selected_project: int
    message: str


def initial_state() -> State:
    """Start with no projects and an example printer size."""
    return State([], 220, 220, 250, "All", -1, "")


def navigation(section: str) -> list:
    """Create sidebar links and highlight the current section."""
    destinations = [
        ("Dashboard", index),
        ("Projects", projects),
        ("Add project", add_project),
        ("Printer settings", settings),
        ("Help", help_page),
    ]
    links = []
    for label, destination in destinations:
        classes = ["planner-nav-link"]
        if label == section:
            classes.append("is-active")
        links.append(Link(label, destination, classes=classes))
    return links


def page(
    state: State, title: str, content: list, section: str = "Projects"
) -> Page:
    """Keep navigation in the sidebar and page content in the main panel."""
    # Paragraphs keep each line of information separate instead of running
    # together. Form components already provide their own grouping.
    body = []
    for item in content:
        if isinstance(item, str):
            body.append(Paragraph(item))
        else:
            body.append(item)

    feedback = []
    if state.message:
        feedback.append(Paragraph(
            state.message, classes=["planner-message"], role="status"
        ))

    # The star adds the items from one list into another component.
    return Page(state, [
        Aside(
            Header("CAD & 3D Print Planner", level=2),
            Paragraph("Plan your next print.", classes=["planner-tagline"]),
            Nav(*navigation(section), aria_label="Main navigation"),
            classes=["planner-sidebar"]
        ),
        Main(
            Header(title, id="planner-page-title"),
            *feedback,
            Div(*body, classes=["planner-content"]),
            id="planner-main", aria_labelledby="planner-page-title"
        )
    ])


def field(label: str, component) -> Div:
    """Keep a form label and its input together, including on small screens."""
    return Div(
        Label(label, for_id=component), component, classes=["planner-field"]
    )


def positive_number(text: str) -> float:
    """Return a positive number, or -1 if the input is invalid."""
    # try/except handles text that cannot become a number.
    try:
        number = float(text)
    except ValueError:
        return -1

    # isfinite rejects special values such as infinity and NaN.
    if not isfinite(number) or number <= 0:
        return -1

    return number


def fits_printer(state: State, project: Project) -> bool:
    """Check the part's size without rotating it."""
    return (
        project.length <= state.printer_length
        and project.width <= state.printer_width
        and project.height <= state.printer_height
    )


def selected(state: State) -> bool:
    """Check whether the selected project still exists."""
    return 0 <= state.selected_project < len(state.projects)


def project_form(project: Project) -> list:
    """Create the fields used to add or edit a project."""
    return [
        field("Project name", TextBox("name", project.name)),
        field("Length (mm)", TextBox("length", str(project.length))),
        field("Width (mm)", TextBox("width", str(project.width))),
        field("Height (mm)", TextBox("height", str(project.height))),
        field("Material", SelectBox(
            "material",
            ["PLA", "PETG", "ABS", "TPU"],
            project.material
        )),
        field(
            "Estimated print time (hours)", TextBox("hours", str(project.hours))
        ),
        field("Status", SelectBox(
            "status",
            ["Planning", "Ready to Print", "Completed"],
            project.status
        )),
        field("Notes", TextArea("notes", project.notes))
    ]


# Drafter can send the current form's inputs when a navigation link
# is clicked. The five navigation routes accept these optional inputs
# so they do not produce warnings about unexpected fields.
# They ignore these inputs. Only Save and Apply actions save changes.


@route
def index(
    state: State,
    name: str = "",
    length: str = "",
    width: str = "",
    height: str = "",
    material: str = "",
    hours: str = "",
    status: str = "",
    notes: str = "",
    printer_length: str = "",
    printer_width: str = "",
    printer_height: str = "",
    status_filter: str = "",
    project_number: str = ""
) -> Page:
    """Show project counts and total estimated print time."""
    completed = 0
    total_hours = 0.0

    for project in state.projects:
        total_hours += project.hours
        if project.status == "Completed":
            completed += 1

    return page(state, "Dashboard", [
        "Plan your CAD parts, check their size, and track your progress.",

        "Projects: " + str(len(state.projects)),

        "Completed: " + str(completed),

        "Total estimated print time: "
        + str(round(total_hours, 2)) + " hours",

        "Printer volume: "
        + str(state.printer_length) + " × "
        + str(state.printer_width) + " × "
        + str(state.printer_height) + " mm",

        "Projects are kept in this session, not a permanent database."
    ], section="Dashboard")


@route
def projects(
    state: State,
    name: str = "",
    length: str = "",
    width: str = "",
    height: str = "",
    material: str = "",
    hours: str = "",
    status: str = "",
    notes: str = "",
    printer_length: str = "",
    printer_width: str = "",
    printer_height: str = "",
    status_filter: str = "",
    project_number: str = ""
) -> Page:
    """Show projects that match the saved status filter."""
    content: list = [
        field("Filter by status", SelectBox(
            "status_filter",
            ["All", "Planning", "Ready to Print", "Completed"],
            state.status_filter
        )),
        Button("Apply filter", apply_filter)
    ]

    options = []

    # enumerate gives the position and the project at that position.
    for position, project in enumerate(state.projects):
        if (
            state.status_filter == "All"
            or project.status == state.status_filter
        ):
            options.append(str(position))
            content.append(
                str(position) + ": " + project.name
                + " | " + project.material
                + " | " + project.status
            )

    if len(options) == 0:
        content.append(
            "No projects match. Add a project or change the filter."
        )
    else:
        content += [
            field(
                "Choose the project number shown above",
                SelectBox("project_number", options)
            ),
            Button("Open project", open_project)
        ]

    return page(state, "Your projects", content)


@route
def apply_filter(
    state: State,
    status_filter: str,
    project_number: str = ""
) -> Page:
    """Save the chosen filter and update the project list."""
    # project_number may arrive from the other control on this page.
    # Applying a filter does not change the selected project.
    if status_filter in [
        "All", "Planning", "Ready to Print", "Completed"
    ]:
        state.status_filter = status_filter
        state.message = ""
    else:
        state.message = "Choose a listed status."

    return projects(state)


@route
def add_project(
    state: State,
    name: str = "",
    length: str = "",
    width: str = "",
    height: str = "",
    material: str = "",
    hours: str = "",
    status: str = "",
    notes: str = "",
    printer_length: str = "",
    printer_width: str = "",
    printer_height: str = "",
    status_filter: str = "",
    project_number: str = ""
) -> Page:
    """Show a form for a new project."""
    blank = Project("", 1, 1, 1, "PLA", 1, "Planning", "")

    return page(
        state,
        "Add a project",
        project_form(blank)
        + [Button("Save new project", save_project)],
        section="Add project"
    )


@route
def save_project(
    state: State,
    name: str,
    length: str,
    width: str,
    height: str,
    material: str,
    hours: str,
    status: str,
    notes: str
) -> Page:
    """Check the form and save a new project."""
    return store_project(
        state, name, length, width, height,
        material, hours, status, notes, False
    )


def store_project(
    state: State,
    name: str,
    length: str,
    width: str,
    height: str,
    material: str,
    hours: str,
    status: str,
    notes: str,
    editing: bool
) -> Page:
    """Check information before adding or changing a project."""
    part = Project(
        name.strip(),
        positive_number(length),
        positive_number(width),
        positive_number(height),
        material,
        positive_number(hours),
        status,
        notes
    )

    if (
        part.name == ""
        or part.length <= 0
        or part.width <= 0
        or part.height <= 0
        or part.hours <= 0
    ):
        state.message = (
            "Enter a project name and positive finite "
            "dimensions and hours."
        )

    elif material not in ["PLA", "PETG", "ABS", "TPU"]:
        state.message = "Choose a listed material."
        part.material = "PLA"

    elif status not in ["Planning", "Ready to Print", "Completed"]:
        state.message = "Choose a listed status."
        part.status = "Planning"

    else:
        if editing:
            state.projects[state.selected_project] = part
        else:
            state.projects.append(part)
            state.selected_project = len(state.projects) - 1

        state.message = "Project saved."
        return detail(state)

    # Keep dropdown values valid if a request contains a bad choice.
    if part.material not in ["PLA", "PETG", "ABS", "TPU"]:
        part.material = "PLA"

    if part.status not in ["Planning", "Ready to Print", "Completed"]:
        part.status = "Planning"

    # A function can be stored in a variable and used by a Button.
    action = save_project
    if editing:
        action = update_project

    return page(
        state,
        "Correct project details",
        project_form(part) + [Button("Save project", action)],
        section="Projects" if editing else "Add project"
    )


@route
def open_project(
    state: State,
    project_number: str,
    status_filter: str = ""
) -> Page:
    """Select a project from its number in the list."""
    # status_filter may arrive with the project number.
    # Opening a project does not apply an unsaved filter.

    # This comprehension creates the allowed project-number strings.
    allowed_numbers = [
        str(number) for number in range(len(state.projects))
    ]

    if project_number in allowed_numbers:
        state.selected_project = int(project_number)
        state.message = ""
        return detail(state)

    state.message = (
        "That project is unavailable. Choose a project from the list."
    )
    return projects(state)


@route
def detail(state: State) -> Page:
    """Show a part's information and its printer-fit result."""
    if not selected(state):
        state.message = "Select a project first."
        return projects(state)

    part = state.projects[state.selected_project]
    fit_message = "Fits the printer in the entered orientation."

    if not fits_printer(state, part):
        fit_message = (
            "Too large: at least one dimension "
            "exceeds the printer volume."
        )

    return page(state, part.name, [
        "Dimensions: "
        + str(part.length) + " × "
        + str(part.width) + " × "
        + str(part.height) + " mm",

        "Material: " + part.material,

        "Print time: " + str(part.hours) + " hours",

        "Status: " + part.status,

        "Notes: " + part.notes,

        fit_message,

        Button("Add another project", add_project),

        Button("Edit project or status", edit_project),

        Button("Review deletion", confirm_delete)
    ])


@route
def edit_project(state: State) -> Page:
    """Show the selected project's information in an editing form."""
    if not selected(state):
        return detail(state)

    return page(
        state,
        "Edit project",
        project_form(state.projects[state.selected_project])
        + [Button("Save changes", update_project)]
    )


@route
def update_project(
    state: State,
    name: str,
    length: str,
    width: str,
    height: str,
    material: str,
    hours: str,
    status: str,
    notes: str
) -> Page:
    """Check edited information and update the selected project."""
    if not selected(state):
        return detail(state)

    return store_project(
        state, name, length, width, height,
        material, hours, status, notes, True
    )


@route
def confirm_delete(state: State) -> Page:
    """Ask the user before deleting a project."""
    if not selected(state):
        return detail(state)

    return page(state, "Delete project?", [
        state.projects[state.selected_project].name,
        "This removes the project from this session.",
        Button("Yes, delete project", delete_project),
        Button("Keep project", detail)
    ])


@route
def delete_project(state: State) -> Page:
    """Delete the selected project and clear the selection."""
    if selected(state):
        state.projects.pop(state.selected_project)
        state.selected_project = -1
        state.message = "Project deleted."
    else:
        state.message = "No project selected."

    return projects(state)


@route
def settings(
    state: State,
    name: str = "",
    length: str = "",
    width: str = "",
    height: str = "",
    material: str = "",
    hours: str = "",
    status: str = "",
    notes: str = "",
    printer_length: str = "",
    printer_width: str = "",
    printer_height: str = "",
    status_filter: str = "",
    project_number: str = ""
) -> Page:
    """Show fields for changing the printer's build volume."""
    return page(state, "Printer settings", [
        "Use the usable build volume from your printer documentation.",

        field("Length (mm)", TextBox("printer_length", str(state.printer_length))),
        field("Width (mm)", TextBox("printer_width", str(state.printer_width))),
        field("Height (mm)", TextBox("printer_height", str(state.printer_height))),

        Button("Save printer settings", save_settings)
    ], section="Printer settings")


@route
def save_settings(
    state: State,
    printer_length: str,
    printer_width: str,
    printer_height: str
) -> Page:
    """Save printer dimensions only when all three are valid."""
    length = positive_number(printer_length)
    width = positive_number(printer_width)
    height = positive_number(printer_height)

    if length <= 0 or width <= 0 or height <= 0:
        state.message = (
            "Printer dimensions must be positive finite numbers."
        )
    else:
        state.printer_length = length
        state.printer_width = width
        state.printer_height = height
        state.message = (
            "Printer settings saved. "
            "Project fit checks now use this volume."
        )

    return settings(state)


@route
def help_page(
    state: State,
    name: str = "",
    length: str = "",
    width: str = "",
    height: str = "",
    material: str = "",
    hours: str = "",
    status: str = "",
    notes: str = "",
    printer_length: str = "",
    printer_width: str = "",
    printer_height: str = "",
    status_filter: str = "",
    project_number: str = ""
) -> Page:
    """Explain how to use the planner."""
    return page(state, "How to use the planner", [
        "1. Set the printer build volume in millimeters.",
        "2. Add your part dimensions, material, hours, status, and notes.",
        "3. Open a project to check fit. Edit it to change its status.",
        "4. Filter projects by Planning, Ready to Print, or Completed.",
        "The fit check compares sizes without rotating the part.",
        "It does not account for supports, adhesion, or clearances.",
        "Print time is your estimate from a slicer.",
        "Projects are session data. Keep important information elsewhere."
    ], section="Help")


# Drafter runs this file on the computer and again in the browser.
# Register the CSS in both places so it survives Pyodide initialization.
add_website_css("""
    body {
        margin: 0;
        background-color: #F1F5F9;
    }

    #drafter-body-- {
        display: grid;
        grid-template-columns: 240px minmax(0, 1fr);
        align-items: start;
        gap: 28px;
        box-sizing: border-box;
        width: 100%;
        max-width: 1440px;
        min-height: 100vh;
        margin: 0 auto;
        padding: 24px;
        background-color: #F1F5F9;
        font-family: Arial, sans-serif;
        font-size: 16px;
        line-height: 1.6;
        color: #14243B;
    }

    #drafter-body-- * {
        box-sizing: border-box;
    }

    #drafter-body-- .planner-sidebar {
        position: sticky;
        top: 24px;
        min-height: calc(100vh - 48px);
        padding: 28px 18px;
        background-color: #14243B;
        color: white;
        border-radius: 16px;
    }

    #drafter-body-- .planner-sidebar h2 {
        margin: 0 10px;
        font-size: 23px;
        line-height: 1.35;
        color: white;
    }

    #drafter-body-- .planner-tagline {
        margin: 12px 10px 32px;
        color: #BDCCE1;
        font-size: 14px;
    }

    #drafter-body-- nav {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    #drafter-body-- .planner-nav-link {
        display: block;
        margin: 0;
        padding: 12px 16px;
        border-radius: 8px;
        color: #E2E8F0;
        text-decoration: none;
        font-weight: 600;
    }

    #drafter-body-- .planner-nav-link:hover {
        background-color: #243A56;
        color: white;
    }

    #drafter-body-- .planner-nav-link.is-active {
        background-color: #2563EB;
        color: white;
    }

    #drafter-body-- a:focus-visible,
    #drafter-body-- button:focus-visible,
    #drafter-body-- input:focus-visible,
    #drafter-body-- select:focus-visible,
    #drafter-body-- textarea:focus-visible {
        outline: 3px solid #60A5FA;
        outline-offset: 3px;
    }

    #drafter-body-- #planner-main {
        min-width: 0;
        min-height: calc(100vh - 48px);
        padding: 36px;
        background-color: white;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        overflow-wrap: anywhere;
    }

    #drafter-body-- #planner-main h1 {
        margin: 0 0 28px;
        padding: 0 0 20px;
        border-bottom: 1px solid #E2E8F0;
        color: #14243B;
        /* Override the default Drafter theme's important heading sizes. */
        font-size: 32px !important;
        line-height: 1.25 !important;
        letter-spacing: normal !important;
    }

    #drafter-body-- .planner-content {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 18px;
    }

    #drafter-body-- .planner-content p {
        margin: 0;
    }

    #drafter-body-- .planner-field {
        width: 100%;
        max-width: 560px;
    }

    #drafter-body-- .planner-field label {
        display: block;
        margin-bottom: 6px;
        font-weight: 600;
    }

    #drafter-body-- .planner-field input,
    #drafter-body-- .planner-field select,
    #drafter-body-- .planner-field textarea {
        display: block;
        width: 100%;
        min-width: 0;
        max-width: 100%;
        margin: 0;
        padding: 10px 12px;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        background-color: white;
        color: #14243B;
        font: inherit;
    }

    #drafter-body-- .planner-field textarea {
        min-height: 110px;
        resize: vertical;
    }

    #drafter-body-- #planner-main button {
        max-width: 100%;
        margin: 0;
        padding: 11px 18px;
        border: 0;
        border-radius: 8px;
        background-color: #2563EB;
        color: white;
        font: inherit;
        font-weight: 600;
        cursor: pointer;
    }

    #drafter-body-- #planner-main button:hover {
        background-color: #1D4ED8;
    }

    #drafter-body-- .planner-message {
        margin: 0 0 24px;
        padding: 12px 16px;
        border-left: 4px solid #2563EB;
        border-radius: 6px;
        background-color: #EFF6FF;
    }

    @media (max-width: 700px) {
        #drafter-body-- {
            grid-template-columns: minmax(0, 1fr);
            gap: 16px;
            padding: 16px;
        }

        #drafter-body-- .planner-sidebar {
            position: static;
            min-height: 0;
            padding: 20px 16px;
        }

        #drafter-body-- .planner-sidebar h2 {
            font-size: 21px;
        }

        #drafter-body-- .planner-tagline {
            margin-bottom: 20px;
        }

        #drafter-body-- nav {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        #drafter-body-- .planner-nav-link {
            padding: 10px 12px;
            font-size: 14px;
        }

        #drafter-body-- #planner-main {
            min-height: 0;
            padding: 24px 20px;
        }

        #drafter-body-- #planner-main h1 {
            font-size: 28px !important;
        }
    }
""")

# Set the site information during the computer's build step only.
# "emscripten" identifies Python running through Pyodide in the browser.
# This avoids repeating the metadata updates that caused the red errors.
if sys.platform != "emscripten":
    set_site_information(
        author="Ian Land",
        description="A CAD and 3D printing project planner.",
        sources=[
            "Drafter documentation",
        ],
        planning="Copy of CS1 Final Project 1_ Design (1).docx",
        links=["https://github.com/Ianland1/cad-print-planner"]
    )


# This guard prevents the server from starting when tests import the file.
if __name__ == "__main__":
    start_server(initial_state(), engine="pyodide")
