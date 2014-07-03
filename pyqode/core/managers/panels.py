"""
This module contains the panels controller, responsible of drawing panel
inside CodeEdit's margins
"""
import logging
from pyqode.core.api.utils import TextHelper
from pyqode.core.api.manager import Manager
from pyqode.core.api.panel import Panel


def _logger():
    return logging.getLogger(__name__)


class PanelsManager(Manager):
    """
    Manages the list of panels and draws them inised the margin of the code
    edit widget.

    """
    def __init__(self, editor):
        super().__init__(editor)
        self._cached_cursor_pos = (-1, -1)
        self._margin_sizes = (0, 0, 0, 0)
        self._top = self._left = self._right = self._bottom = -1
        self._panels = {
            Panel.Position.TOP: {},
            Panel.Position.LEFT: {},
            Panel.Position.RIGHT: {},
            Panel.Position.BOTTOM: {}
        }
        editor.blockCountChanged.connect(self._update_viewport_margins)
        editor.updateRequest.connect(self.update)

    def append(self, panel, position=Panel.Position.LEFT):
        """
        Install a panel on the editor.

        :param panel: Panel to install
        :param position: Panel position
        :return: The installed panel
        """
        assert panel is not None
        pos_to_string = {
            Panel.Position.BOTTOM: 'bottom',
            Panel.Position.LEFT: 'left',
            Panel.Position.RIGHT: 'right',
            Panel.Position.TOP: 'top'
        }
        _logger().info('adding panel %s at %r', panel.name,
                        pos_to_string[position])
        panel.order_in_zone = len(self._panels[position])
        self._panels[position][panel.name] = panel
        panel.position = position
        panel.on_install(self.editor)
        _logger().debug('panel %s installed', panel.name)
        return panel

    def remove(self, name_or_klass):
        """
        Removes the specified panel.

        :param name_or_klass: Name or class of the panel to remove.
        :return: The removed panel
        """
        _logger().info('removing panel %r', name_or_klass)
        panel = self.get(name_or_klass)
        panel.on_uninstall()
        return self._panels[panel.position].pop(panel.name, None)

    def clear(self):
        """
        Removes all panel from the editor.

        """
        for i in range(4):
            while len(self._panels[i]):
                key = list(self._panels[i].keys())[0]
                panel = self.remove(key)
                del panel

    def get(self, name_or_klass):
        """
        Gets a specific panel instance.

        :param name_or_klass: Name or class of the panel to retrieve.
        :return: The specified panel instance.
        """
        if not isinstance(name_or_klass, str):
            name_or_klass = name_or_klass.__name__
        for zone in range(4):
            try:
                panel = self._panels[zone][name_or_klass]
            except KeyError:
                pass
            else:
                return panel
        raise KeyError(name_or_klass)

    def __iter__(self):
        lst = []
        for zone, zone_dict in self._panels.items():
            for name, panel in zone_dict.items():
                lst.append(panel)
        return iter(lst)

    def __len__(self):
        lst = []
        for zone, zone_dict in self._panels.items():
            for name, panel in zone_dict.items():
                lst.append(panel)
        return len(lst)

    def panels_for_zone(self, zone):
        """
        Gets the list of panels attached to the specified zone.

        :param zone: Panel position.

        :return: List of panels instances.
        """
        return list(self._panels[zone].values())

    def refresh(self):
        """ Refreshes the editor panels (resize and update margins) """
        _logger().debug('refresh_panels')
        self.resize()
        self.update(self.editor.contentsRect(), 0, force_update_margins=True)

    def resize(self):
        """ Resizes panels """
        # pylint: disable=too-many-locals
        content_rect = self.editor.contentsRect()
        viewport_content_rect = self.editor.viewport().contentsRect()
        s_bottom, s_left, s_right, s_top = self._compute_zones_sizes()
        w_offset = content_rect.width() - (viewport_content_rect.width() +
                                           s_left + s_right)
        h_offset = content_rect.height() - (viewport_content_rect.height() +
                                            s_bottom + s_top)
        left = 0
        panels = self.panels_for_zone(Panel.Position.LEFT)
        panels.sort(key=lambda panel: panel.order_in_zone, reverse=True)
        for panel in panels:
            if not panel.isVisible():
                continue
            panel.adjustSize()
            size_hint = panel.sizeHint()
            panel.setGeometry(content_rect.left() + left,
                              content_rect.top() + s_top,
                              size_hint.width(),
                              content_rect.height() - s_bottom - s_top -
                              h_offset)
            left += size_hint.width()
        right = 0
        panels = self.panels_for_zone(Panel.Position.RIGHT)
        panels.sort(key=lambda panel: panel.order_in_zone, reverse=True)
        for panel in panels:
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            panel.setGeometry(content_rect.right() - right -
                              size_hint.width() - w_offset,
                              content_rect.top(), size_hint.width(),
                              content_rect.height() - h_offset)
            right += size_hint.width()
        top = 0
        panels = self.panels_for_zone(Panel.Position.TOP)
        panels.sort(key=lambda panel: panel.order_in_zone)
        for panel in panels:
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            panel.setGeometry(content_rect.left(), content_rect.top() + top,
                              content_rect.width() - w_offset,
                              size_hint.height())
            top += size_hint.height()
        bottom = 0
        panels = self.panels_for_zone(Panel.Position.BOTTOM)
        panels.sort(key=lambda panel: panel.order_in_zone)
        for panel in panels:
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            panel.setGeometry(content_rect.left(),
                              content_rect.bottom() - bottom -
                              size_hint.height() - h_offset,
                              content_rect.width() - w_offset,
                              size_hint.height())
            bottom += size_hint.height()

    def update(self, rect, delta_y, force_update_margins=False):
        """ Updates panels """
        helper = TextHelper(self.editor)
        if not self:
            return
        for zones_id, zone in self._panels.items():
            if zones_id == Panel.Position.TOP or \
               zones_id == Panel.Position.BOTTOM:
                continue
            panels = list(zone.values())
            for panel in panels:
                if not panel.scrollable:
                    continue
                if delta_y:
                    panel.scroll(0, delta_y)
                else:
                    line, col = helper.cursor_position()
                    oline, ocol = self._cached_cursor_pos
                    if line != oline or col != ocol:
                        panel.update(0, rect.y(), panel.width(), rect.height())
                    self._cached_cursor_pos = helper.cursor_position()
        if (rect.contains(self.editor.viewport().rect()) or
                force_update_margins):
            # _logger().debug('_update_panels -> _update_viewport_margins')
            self._update_viewport_margins()

    def _update_viewport_margins(self):
        """ Update viewport margins """
        top = 0
        left = 0
        right = 0
        bottom = 0
        # _logger().debug('updating viewport margins')
        # _logger().debug('processing left panels')
        for panel in self.panels_for_zone(Panel.Position.LEFT):
            if panel.isVisible():
                width = panel.sizeHint().width()
                # _logger().debug('right panel width: %r', width)
                left += width
            # else:
                # _logger().debug('skipping invisible panel %r', panel.name)
        # _logger().debug('processing right panels')
        for panel in self.panels_for_zone(Panel.Position.RIGHT):
            if panel.isVisible():
                width = panel.sizeHint().width()
                # _logger().debug('right panel width: %r', width)
                right += width
            # else:
                # _logger().debug('skipping invisible panel %s', panel.name)
        # _logger().debug('processing top panels')
        for panel in self.panels_for_zone(Panel.Position.TOP):
            if panel.isVisible():
                height = panel.sizeHint().height()
                # _logger().debug('_bottom panel height: %r', height)
                top += height
            # else:
                # _logger().debug('skipping invisible panel %s', panel.name)
        # _logger().debug('processing _bottom panels')
        for panel in self.panels_for_zone(Panel.Position.BOTTOM):
            if panel.isVisible():
                height = panel.sizeHint().height()
                # _logger().debug('_bottom panel height: %r', height)
                bottom += height
            # else:
                # _logger().debug('skipping invisible panel %s', panel.name)
        self._margin_sizes = (top, left, right, bottom)
        self.editor.setViewportMargins(left, top, right, bottom)
        # _logger().debug('viewport margins updated: %r', repr(
        #     self._margin_sizes))

    def margin_size(self, position=Panel.Position.LEFT):
        """
        Gets the size of a specific margin.

        :param position: Margin position. See
            :class:`pyqode.core.api.Panel.Position`
        :return: The size of the specified margin
        :rtype: float
        """
        return self._margin_sizes[position]

    def _compute_zones_sizes(self):
        """ Compute panel zone sizes """
        # Left panels
        left = 0
        for panel in self.panels_for_zone(Panel.Position.LEFT):
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            left += size_hint.width()
        # Right panels
        right = 0
        for panel in self.panels_for_zone(Panel.Position.RIGHT):
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            right += size_hint.width()
        # Top panels
        top = 0
        for panel in self.panels_for_zone(Panel.Position.TOP):
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            top += size_hint.height()
        # Bottom panels
        bottom = 0
        for panel in self.panels_for_zone(Panel.Position.BOTTOM):
            if not panel.isVisible():
                continue
            size_hint = panel.sizeHint()
            bottom += size_hint.height()
        self._top, self._left, self._right, self._bottom = (
            top, left, right, bottom)
        return bottom, left, right, top