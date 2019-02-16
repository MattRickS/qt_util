from itertools import groupby, count

from PySide2 import QtCore, QtGui, QtWidgets


class HeaderView(QtWidgets.QHeaderView):
    # TODO: Hijack the model data for the actual columns to replace text for
    # collapsed columns with '...'
    BTN_MARGIN = 2
    BTN_SIZE = 16

    def __init__(self, orientation, parent=None):
        super(HeaderView, self).__init__(orientation, parent)
        self._groups = {}

    def mouseMoveEvent(self, event):
        super(HeaderView, self).mouseMoveEvent(event)
        logical = self.logicalIndexAt(event.pos())
        if logical >= 0 and self.has_button(logical):
            # Update the section to ensure the button highlights are enabled
            # when the mouse travels over
            self.updateSection(logical)

    def mousePressEvent(self, event):
        # type: (QtCore.QEvent) -> None
        logical = self.logicalIndexAt(event.pos())
        btn_rect = self.get_button_rect(logical)
        if btn_rect is not None and btn_rect.contains(event.pos()):
            name, data = self._get_group_data(logical)
            self.set_group_collapsed(name, not data['collapsed'])
            return
        super(HeaderView, self).mousePressEvent(event)

    def paintSection(self, painter, rect, logical_index):
        # type: (QtGui.QPainter, QtCore.QRect, int) -> None
        if not rect.isValid():
            return

        painter.save()
        style = self.style()

        opt = self.get_section_style_option(logical_index)
        opt.rect = rect

        # Check if the index is the last column of a group and add a button
        btn_opt = None
        btn = None
        grp = self._get_group_data(logical_index)
        if grp is not None:
            name, data = grp
            if data['indexes'][-1] == logical_index:
                btn = QtWidgets.QPushButton()
                btn_opt = QtWidgets.QStyleOptionButton()
                btn.initStyleOption(btn_opt)
                btn_opt.rect = self._get_button_rect(rect)
                horizontal = self.orientation() == QtCore.Qt.Horizontal
                btn_opt.text = (('>' if horizontal else 'v')
                                if data['collapsed'] else
                                ('<' if horizontal else '^'))
                if data['collapsed']:
                    opt.textAlignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
                    opt.text = name
            # Set the background colour for all the grouped column headers
            opt.palette.setColor(QtGui.QPalette.All, QtGui.QPalette.Background, data['colour'])

        # Update the state based on the current mouse state in relation to the
        # section rect
        mouse_pos = self.mapFromGlobal(QtGui.QCursor.pos())
        if btn_opt is not None and btn_opt.rect.contains(mouse_pos):
            if QtWidgets.QApplication.mouseButtons() & QtCore.Qt.LeftButton:
                btn_opt.state |= QtWidgets.QStyle.State_Sunken
            else:
                btn_opt.state |= QtWidgets.QStyle.State_MouseOver
        elif opt.rect.contains(mouse_pos):
            if QtWidgets.QApplication.mouseButtons() & QtCore.Qt.LeftButton:
                opt.state |= QtWidgets.QStyle.State_Sunken
            else:
                opt.state |= QtWidgets.QStyle.State_MouseOver

        # style.drawControl(QtWidgets.QStyle.CE_HeaderSection, opt, painter, self)
        painter.setBrush(opt.palette.background())
        painter.drawRect(rect)

        # Horizontal header labels look wrong if not equally aligned - only
        # modify the header for columns with a button
        # Vertical header labels look wrong if not aligned horizontally, so all
        # columns in a group should share the indent, not just the button column
        if btn is not None or (self.orientation() == QtCore.Qt.Vertical and grp is not None):
            text_rect = style.subElementRect(QtWidgets.QStyle.SE_HeaderLabel, opt)
            opt.rect = text_rect.adjusted(0, 0, -(self.BTN_SIZE + self.BTN_MARGIN * 2), 0)
        style.drawControl(QtWidgets.QStyle.CE_HeaderLabel, opt, painter, self)

        # WIP: sortIndicator drawing
        if opt.sortIndicator:
            opt.rect = style.subElementRect(QtWidgets.QStyle.SE_HeaderArrow, opt)
            style.proxy().drawPrimitive(QtWidgets.QStyle.PE_IndicatorHeaderArrow, opt, painter)

        if btn is not None:
            style.drawControl(QtWidgets.QStyle.CE_PushButton, btn_opt, painter, btn)

        painter.restore()

    def sectionSizeFromContents(self, logical_index):
        # type: (int) -> QtCore.QSize
        size = super(HeaderView, self).sectionSizeFromContents(logical_index)
        grp = self._get_group_data(logical_index)
        if grp is not None:
            name, data = grp
            # If the index has a button, modify the size
            if data['indexes'][-1] == logical_index:
                opt = QtWidgets.QStyleOptionHeader()
                self.initStyleOption(opt)
                # Use the group name if collapsed, or header label if not
                if not data['collapsed']:
                    name = self.model().headerData(logical_index,
                                                   self.orientation(),
                                                   QtCore.Qt.DisplayRole)
                margins = self.style().pixelMetric(QtWidgets.QStyle.PM_HeaderMargin, opt) * 2
                text_width = max(size.width(), opt.fontMetrics.width(name))
                size = QtCore.QSize(text_width + self.BTN_SIZE + self.BTN_MARGIN * 2 + margins,
                                    size.height())
        return size

    def add_group(self, name, indexes, collapsed=False, colour=None):
        # type: (str, list[int], bool, QtGui.QColor) -> None
        # Ensure each index is only contained in one group
        for group_name, group_data in self._groups.items():
            overlap = set(group_data['indexes']) & set(indexes)
            if overlap:
                self._groups[group_name] = [i for i in indexes if i not in indexes]

        # Ensure all visual indexes are in order
        visuals = sorted(self.visualIndex(idx) for idx in indexes)
        logical_in_visual_order = []
        minimum = visuals[0]
        for idx, visual_index in enumerate(visuals):
            ordered_visual_index = minimum + idx
            if visual_index != ordered_visual_index:
                self.moveSection(visual_index, ordered_visual_index)
            logical_in_visual_order.append(self.logicalIndex(ordered_visual_index))

        btn_index = logical_in_visual_order[-1]
        self._groups[name] = {
            'colour': colour or QtGui.QColor('red'),
            'indexes': logical_in_visual_order,
            'collapsed': collapsed,
            'size': self.sectionSize(btn_index),
        }

        # Expand / collapse if any of the indexes are collapsed
        self.set_group_collapsed(name, collapsed)

        # TODO: Replace hack fix
        # If not collapsing, the size is the same and nothing is recalculated,
        # which prevents the custom header size (including button) being applied
        if not collapsed:
            hidden_state = self.isSectionHidden(btn_index)
            self.setSectionHidden(btn_index, not hidden_state)
            self.setSectionHidden(btn_index, hidden_state)

    def get_button_rect(self, logical_index):
        # type: (int) -> QtCore.QRect|None
        grp = self._get_group_data(logical_index)
        if grp is None:
            return
        rect = self.get_section_rect(logical_index)
        return self._get_button_rect(rect)

    def get_section_rect(self, logical_index):
        # type: (int) -> QtCore.QRect
        # Accumulate the offset from the
        distance = self.offset()
        for visual_index in range(self.count()):
            logical = self.logicalIndex(visual_index)
            if self.isSectionHidden(logical):
                continue
            if logical == logical_index:
                size = self.sectionSize(logical)
                if self.orientation() == QtCore.Qt.Horizontal:
                    rect = QtCore.QRect(distance, 0, size, self.height())
                else:
                    rect = QtCore.QRect(0, distance, self.width(), size)
                return rect
            distance += self.sectionSize(logical)

    def get_section_style_option(self, logical_index):
        # type: (int) -> QtWidgets.QStyleOptionHeader
        model = self.model()
        orientation = self.orientation()
        root = self.rootIndex()
        selection_model = self.selectionModel()
        style = self.style()

        opt = QtWidgets.QStyleOptionHeader()
        self.initStyleOption(opt)

        # State
        state = QtWidgets.QStyle.State_None
        if self.isEnabled():
            state |= QtWidgets.QStyle.State_Enabled
        if self.window().isActiveWindow():
            state |= QtWidgets.QStyle.State_Active
        if self.sectionsClickable() and selection_model and self.highlightSections():
            if orientation == QtCore.Qt.Horizontal:
                if selection_model.columnIntersectsSelection(logical_index, root):
                    state |= QtWidgets.QStyle.State_On
                if selection_model.isColumnSelected(logical_index, root):
                    state |= QtWidgets.QStyle.State_Sunken
            else:
                if selection_model.rowIntersectsSelection(logical_index, root):
                    state |= QtWidgets.QStyle.State_On
                if selection_model.isRowSelected(logical_index, root):
                    state |= QtWidgets.QStyle.State_Sunken
        opt.state |= state

        # Margin
        margin = 2 * style.pixelMetric(QtWidgets.QStyle.PM_HeaderMargin, opt, self)
        header_arrow_alignment = style.styleHint(QtWidgets.QStyle.SH_Header_ArrowAlignment, opt, self)
        is_header_arrow_on_the_side = header_arrow_alignment & QtCore.Qt.AlignVCenter
        if (self.isSortIndicatorShown()
                and self.sortIndicatorSection() == logical_index
                and is_header_arrow_on_the_side):
            margin += style.pixelMetric(QtWidgets.QStyle.PM_HeaderMarkSize, opt, self)

        # Icon
        opt.iconAlignment = QtCore.Qt.AlignVCenter
        icon = model.headerData(logical_index, orientation, QtCore.Qt.DecorationRole)
        if icon and not icon.isNull():
            opt.icon = icon
            margin += (style.pixelMetric(QtWidgets.QStyle.PM_SmallIconSize, opt, self) +
                       style.pixelMetric(QtWidgets.QStyle.PM_HeaderMargin, opt, self))

        # Text
        text_alignment = model.headerData(logical_index, orientation,
                                          QtCore.Qt.TextAlignmentRole)
        opt.textAlignment = text_alignment or QtCore.Qt.AlignCenter  # d.defaultAlignment
        opt.text = model.headerData(logical_index, orientation, QtCore.Qt.DisplayRole)
        if self.textElideMode() != QtCore.Qt.ElideNone:
            text_rect = style.subElementRect(QtWidgets.QStyle.SE_HeaderLabel, opt, self)
            opt.text = opt.fontMetrics.elidedText(opt.text, self.textElideMode(),
                                                  text_rect.width() - margin)

        # Brushes
        background_brush = model.headerData(logical_index, orientation, QtCore.Qt.BackgroundRole)
        if background_brush is not None:
            brush = QtGui.QBrush(background_brush)
            opt.palette.setBrush(QtGui.QPalette.Button, brush)
            opt.palette.setBrush(QtGui.QPalette.Window, brush)

        foreground_brush = model.headerData(logical_index, orientation, QtCore.Qt.ForegroundRole)
        if foreground_brush is not None:
            opt.palette.setBrush(QtGui.QPalette.ButtonText, QtGui.QBrush(foreground_brush))

        # Header section attributes
        if self.isSortIndicatorShown() and self.sortIndicatorSection() == logical_index:
            opt.sortIndicator = (QtWidgets.QStyleOptionHeader.SortDown
                                 if (self.sortIndicatorOrder() == QtCore.Qt.AscendingOrder) else
                                 QtWidgets.QStyleOptionHeader.SortUp)
        opt.section = logical_index
        opt.orientation = orientation

        # Position
        visual = self.visualIndex(logical_index)
        first = self.logicalIndex(0) == logical_index
        last = self.logicalIndex(self.count() - 1) == logical_index
        if first and last:
            opt.position = QtWidgets.QStyleOptionHeader.OnlyOneSection
        elif first:
            opt.position = (QtWidgets.QStyleOptionHeader.End
                            if self.isRightToLeft() else
                            QtWidgets.QStyleOptionHeader.Beginning)
        elif last:
            opt.position = (QtWidgets.QStyleOptionHeader.Beginning
                            if self.isRightToLeft() else
                            QtWidgets.QStyleOptionHeader.End)
        else:
            opt.position = QtWidgets.QStyleOptionHeader.Middle

        # Selection
        if self.orientation() == QtCore.Qt.Horizontal:
            previous_selected = self.selectionModel().isColumnSelected(
                self.logicalIndex(visual - 1), root)
            next_selected = self.selectionModel().isColumnSelected(
                self.logicalIndex(visual + 1), root)
        else:
            previous_selected = self.selectionModel().isRowSelected(
                self.logicalIndex(visual - 1), root)
            next_selected = self.selectionModel().isRowSelected(
                self.logicalIndex(visual + 1), root)
        if previous_selected and next_selected:
            opt.selectedPosition = QtWidgets.QStyleOptionHeader.NextAndPreviousAreSelected
        elif previous_selected:
            opt.selectedPosition = QtWidgets.QStyleOptionHeader.PreviousIsSelected
        elif next_selected:
            opt.selectedPosition = QtWidgets.QStyleOptionHeader.NextIsSelected
        else:
            opt.selectedPosition = QtWidgets.QStyleOptionHeader.NotAdjacent

        return opt

    def has_button(self, logical_index):
        # type: (int) -> bool
        grp = self._get_group_data(logical_index)
        return grp is None or logical_index == grp[1]['indexes'][-1]

    def is_collapsed_group(self, name):
        # type: (str) -> bool|None
        return self._groups.get(name, {}).get('collapsed')

    def is_collapsed_index(self, logical_index):
        # type: (int) -> bool
        for data in self._groups.values():
            if logical_index in data['indexes']:
                return data['collapsed']
        return False

    def is_grouped(self, logical_index):
        # type: (int) -> bool
        return self._get_group_data(logical_index) is not None

    def remove_group(self, name):
        # type: (str) -> bool
        removed = self.set_group_collapsed(name, False)
        self._groups.pop(name, None)
        return removed

    def set_group_collapsed(self, name, collapsed):
        # type: (str, bool) -> bool
        data = self._groups.get(name)
        if not data:
            return False
        # Hide/Show all following indexes
        data['collapsed'] = collapsed
        indexes = data['indexes']
        btn_index = indexes[-1]

        # Font metrics for the name
        if collapsed:
            # [ margin text margin btn_margin btn btn_margin ]
            opt = QtWidgets.QStyleOptionHeader()
            self.initStyleOption(opt)
            size = ((opt.fontMetrics.width(name) + self.style().pixelMetric(QtWidgets.QStyle.PM_HeaderMargin, opt) * 2)
                    if self.orientation() == QtCore.Qt.Horizontal else
                    opt.fontMetrics.height())
            size += self.BTN_SIZE + self.BTN_MARGIN * 2
            # Save the width before replacing it so it can be restored
            data['size'] = self.sectionSize(btn_index)
        else:
            size = data['size']
        self.resizeSection(btn_index, size)

        # Toggle the visibility of the columns
        for index in indexes[:-1]:
            self.setSectionHidden(index, collapsed)

        return True

    def toggle_group(self, name):
        # type: (str) -> None
        data = self._groups.get(name)
        if data:
            self.set_group_collapsed(name, not data['collapsed'])

    def _get_button_rect(self, section_rect):
        # type: (QtCore.QRect) -> QtCore.QRect
        pos = section_rect.topRight()
        btn_height = section_rect.height() - self.BTN_MARGIN * 2
        btn_width = min(self.BTN_SIZE, section_rect.width() - self.BTN_MARGIN * 2)
        return QtCore.QRect(
            pos.x() - self.BTN_MARGIN - btn_width,
            pos.y() + self.BTN_MARGIN,
            btn_width,
            btn_height,
        )

    def _get_group_data(self, logical_index):
        # type: (int) -> tuple[str, dict]
        for name, data in self._groups.items():
            if logical_index in data['indexes']:
                return name, data


if __name__ == '__main__':
    from collections import namedtuple
    import sys

    class EntityModel(QtCore.QAbstractItemModel):
        def __init__(self, columns=None, entities=None, parent=None):
            # type: (tuple, list, QtWidgets.QWidget) -> None
            super(EntityModel, self).__init__(parent)
            self._entities = entities or []
            self.columns = columns or ()

        def add_entities(self, entities, index=None, parent=QtCore.QModelIndex()):
            # type: (list, int, QtCore.QModelIndex) -> None
            start = self.rowCount() if index is None else index
            num = len(entities)
            self.beginInsertRows(parent, start, start + num)
            self.insertRows(start, num, parent)
            self._entities = self._entities[:start] + entities + self._entities[start:]
            self.endInsertRows()

        def remove_entities(self, entities, parent=QtCore.QModelIndex()):
            # Guarantees order, avoids errors for invalid entities (but won't give warning)
            indexes = [idx for idx, e in enumerate(self._entities) if e in entities]
            # Remove in reversed order to prevent modifying indices during loop
            for _, grp in groupby(reversed(indexes), key=lambda x, y=count(): next(y) + x):
                indices = list(grp)
                # Indices are reversed
                end, start = indices[0], indices[-1]
                self.beginRemoveRows(parent, start, end)
                self.removeRows(start, end-start, parent)
                self._entities[start:end + 1] = []
                self.endRemoveRows()

        def set_entities(self, entities):
            # type: (list) -> None
            self.beginResetModel()
            self._entities = entities
            self.endResetModel()

        def columnCount(self, parent=QtCore.QModelIndex()):
            # type: (QtCore.QModelIndex) -> int
            return len(self.columns)

        def data(self, index, role=QtCore.Qt.DisplayRole):
            # type: (QtCore.QModelIndex, int) -> object
            if not index.isValid():
                return
            if role == QtCore.Qt.DisplayRole:
                field = self.columns[index.column()]
                entity = self._entities[index.row()]
                value = getattr(entity, field)
                return str(value)

        def flags(self, index):
            # type: (QtCore.QModelIndex) -> QtCore.Qt.ItemFlags
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
            # type: (int, QtCore.Qt.Orientation, int) -> str
            if role == QtCore.Qt.DisplayRole:
                if orientation == QtCore.Qt.Horizontal:
                    return self.columns[section]
                else:
                    return str(section)

        def index(self, row, column, parent=QtCore.QModelIndex()):
            # type: (int, int, QtCore.QModelIndex) -> QtCore.QModelIndex
            return self.createIndex(row, column, self._entities[row] if self._entities else None)

        def parent(self, child):
            # type: (QtCore.QModelIndex) -> QtCore.QModelIndex
            return QtCore.QModelIndex()

        def rowCount(self, parent=QtCore.QModelIndex()):
            # type: (QtCore.QModelIndex) -> int
            return len(self._entities)

    app = QtWidgets.QApplication(sys.argv)

    attrs = ('name', 'gender', 'age', 'race')
    Entity = namedtuple('Entity', attrs)

    model = EntityModel(attrs, [
        Entity('nuala', 'female', 30, 'human'),
        Entity('matthew', 'male', 30, 'human'),
        Entity('ray', 'male', 30, 'human'),
        Entity('mel', 'male', 31, 'human'),
    ])
    # TODO: Enable sorting on view
    # proxy = QtCore.QSortFilterProxyModel()
    # proxy.setSourceModel(model)
    view = QtWidgets.QTableView()
    header = HeaderView(QtCore.Qt.Horizontal, view)
    view.setHorizontalHeader(header)
    vheader = HeaderView(QtCore.Qt.Vertical, view)
    view.setVerticalHeader(vheader)
    view.setModel(model)
    # view.setSortingEnabled(True)
    header.add_group('Character', [0, 2, 3], collapsed=False)
    vheader.add_group('Half', [1, 2], collapsed=False)
    view.show()
    view.resizeColumnsToContents()
    view.resizeRowsToContents()

    app.exec_()
    sys.exit()
