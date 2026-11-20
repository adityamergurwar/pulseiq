import unittest

import plotly.io as pio

from pulseiq.app_common import _install_plotly_theme


class ResponsiveUiTests(unittest.TestCase):
    def test_shared_chart_theme_reserves_mobile_legend_space(self):
        _install_plotly_theme()
        layout = pio.templates["pulseiq"].layout
        self.assertEqual(layout.legend.orientation, "h")
        self.assertLess(layout.legend.y, 0)
        self.assertGreaterEqual(layout.margin.b, 90)

    def test_shared_chart_theme_uses_compact_responsive_dimensions(self):
        _install_plotly_theme()
        layout = pio.templates["pulseiq"].layout
        self.assertTrue(layout.autosize)
        self.assertLessEqual(layout.height, 440)
        self.assertLessEqual(layout.title.font.size, 17)


if __name__ == "__main__":
    unittest.main(verbosity=2)
