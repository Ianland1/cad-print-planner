"""Tests for the CAD planner.

unittest is Python's built-in testing library.
Each test starts with fresh State so tests do not affect each other.
"""

import unittest
import main as app


class PlannerTests(unittest.TestCase):
    """Test routes, project changes, and printer-fit checks."""

    def setUp(self) -> None:
        """Create fresh information for each test."""
        self.state = app.initial_state()
        self.part = app.Project(
            "Bracket", 50, 40, 30, "PLA", 2, "Planning", "Prototype"
        )

    def add(self) -> None:
        """Add and select an example part."""
        self.state.projects.append(self.part)
        self.state.selected_project = 0

    def test_index(self) -> None:
        """Check the dashboard's counts and hours."""
        self.add()
        self.part.status = "Completed"
        content = app.index(self.state).content

        self.assertIn("Completed: 1", content)
        self.assertIn(
            "Total estimated print time: 2.0 hours", content
        )

    def test_projects(self) -> None:
        """Check both empty and populated project lists."""
        self.assertIn(
            "No projects match. Add a project or change the filter.",
            app.projects(self.state).content
        )

        self.add()
        self.assertIn(
            "0: Bracket | PLA | Planning",
            app.projects(self.state).content
        )

    def test_apply_filter(self) -> None:
        """Check that filtering hides projects with other statuses."""
        self.add()
        result = app.apply_filter(self.state, "Completed")

        self.assertEqual(self.state.status_filter, "Completed")
        self.assertNotIn(
            "0: Bracket | PLA | Planning", result.content
        )

        app.apply_filter(self.state, "Unknown")
        self.assertEqual(self.state.status_filter, "Completed")

    def test_add_project(self) -> None:
        """Opening the form should not create a project."""
        self.assertIn(
            "Project name", app.add_project(self.state).content
        )
        self.assertEqual(self.state.projects, [])

    def test_save_project(self) -> None:
        """Check that valid inputs create the correct Project."""
        app.save_project(
            self.state, " Bracket ", "50", "40", "30",
            "PLA", "2", "Planning", "Prototype"
        )

        self.assertEqual(self.state.projects, [self.part])
        self.assertEqual(self.state.selected_project, 0)

    def test_invalid_project(self) -> None:
        """Check that invalid inputs cannot create projects."""
        for value in ["0", "-1", "abc", "nan", "inf", ""]:
            app.save_project(
                self.state, "Bracket", value, "40", "30",
                "PLA", "2", "Planning", ""
            )
            self.assertEqual(self.state.projects, [])

        bad_choices = [
            ("", "PLA", "Planning"),
            ("Part", "Wood", "Planning"),
            ("Part", "PLA", "Unknown")
        ]

        for name, material, status in bad_choices:
            app.save_project(
                self.state, name, "1", "2", "3",
                material, "1", status, ""
            )
            self.assertEqual(self.state.projects, [])

    def test_open_project(self) -> None:
        """Check valid and invalid project selections."""
        self.add()
        self.state.selected_project = -1

        app.open_project(self.state, "0")
        self.assertEqual(self.state.selected_project, 0)

        for number in ["-1", "1", "abc", "0.0"]:
            app.open_project(self.state, number)
            self.assertIn("unavailable", self.state.message)

    def test_detail(self) -> None:
        """Check fit messages for small and oversized parts."""
        self.add()

        self.assertIn(
            "Fits the printer in the entered orientation.",
            app.detail(self.state).content
        )

        self.part.length = 221
        self.assertIn(
            "Too large: at least one dimension exceeds the printer volume.",
            app.detail(self.state).content
        )

    def test_edit_project(self) -> None:
        """Check that the edit form shows the existing name."""
        self.add()
        content = app.edit_project(self.state).content

        # any returns True when at least one item matches.
        found_name = any(
            isinstance(item, app.TextBox)
            and item.default_value == "Bracket"
            for item in content
        )
        self.assertTrue(found_name)

    def test_update_project(self) -> None:
        """Check successful edits and rejection of invalid edits."""
        self.add()

        app.update_project(
            self.state, "New", "60", "50", "40",
            "PETG", "3", "Completed", "Finished"
        )

        self.assertEqual(len(self.state.projects), 1)
        self.assertEqual(self.state.projects[0].name, "New")
        self.assertEqual(self.state.projects[0].status, "Completed")

        app.update_project(
            self.state, "Bad", "0", "1", "1",
            "PLA", "1", "Planning", ""
        )
        self.assertEqual(self.state.projects[0].name, "New")

    def test_confirm_delete(self) -> None:
        """Opening confirmation should not delete the project."""
        self.add()

        self.assertIn(
            "Bracket", app.confirm_delete(self.state).content
        )
        self.assertEqual(len(self.state.projects), 1)

    def test_delete_project(self) -> None:
        """Delete only the selected project and clear selection."""
        self.add()
        self.state.projects.append(
            app.Project(
                "Other", 1, 1, 1, "PLA", 1, "Planning", ""
            )
        )

        app.delete_project(self.state)

        self.assertEqual(self.state.projects[0].name, "Other")
        self.assertEqual(self.state.selected_project, -1)

        app.delete_project(self.state)
        self.assertEqual(len(self.state.projects), 1)

    def test_settings(self) -> None:
        """Check that printer settings fields are present."""
        self.assertIn(
            "Length (mm)", app.settings(self.state).content
        )

    def test_save_settings(self) -> None:
        """Update valid dimensions and reject invalid ones."""
        app.save_settings(self.state, "100", "110", "120")

        self.assertEqual(
            (
                self.state.printer_length,
                self.state.printer_width,
                self.state.printer_height
            ),
            (100, 110, 120)
        )

        app.save_settings(self.state, "200", "nan", "300")

        self.assertEqual(self.state.printer_length, 100)
        self.assertEqual(self.state.printer_height, 120)

    def test_help_page(self) -> None:
        """Check that Help explains the fit check."""
        self.assertIn(
            "The fit check compares sizes without rotating the part.",
            app.help_page(self.state).content
        )

    def test_fit_boundaries(self) -> None:
        """Equal sizes fit; exceeding any printer axis does not."""
        examples = [
            ((220, 220, 250), True),
            ((221, 1, 1), False),
            ((1, 221, 1), False),
            ((1, 1, 251), False)
        ]

        for dimensions, expected in examples:
            # The star passes the three dimensions as separate arguments.
            part = app.Project(
                "Part", *dimensions, "PLA", 1, "Planning", ""
            )
            self.assertEqual(
                app.fits_printer(self.state, part), expected
            )

    def test_unselected_routes(self) -> None:
        """Handle missing selections without crashing."""
        for action in [
            app.detail, app.edit_project, app.confirm_delete
        ]:
            self.assertIn(
                "Select a project first.",
                action(self.state).content
            )

        app.update_project(
            self.state, "Part", "1", "1", "1",
            "PLA", "1", "Planning", ""
        )
        self.assertEqual(self.state.projects, [])


if __name__ == "__main__":
    unittest.main()
