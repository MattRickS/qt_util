from itertools import groupby, count

from PySide2 import QtCore, QtGui, QtWidgets


class HeaderView(QtWidgets.QHeaderView):
    # TODO: Hijack the model data for the actual columns to replace text for
    # collapsed columns with '...'
    BTN_MARGIN = 2
    BTN_WIDTH = 16

    def __init__(self, orientation, parent=None):
        super(HeaderView, self).__init__(orientation, parent)
        self._groups = {}

    # def mouseMoveEvent(self, event):
    #     super(HeaderView, self).mouseMoveEvent(event)
    #     logical = self.logicalIndexAt(event.pos())
    #     if logical >= 0:
    #         painter = QtGui.QPainter(self.viewport())
    #         rect = self.get_section_rect(logical)
    #         print('Repainting')
    #         self.paintSection(painter, rect, logical)

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
        if grp:
            name, data = grp
            if data['indexes'][-1] == logical_index:
                btn = QtWidgets.QPushButton()
                btn_opt = QtWidgets.QStyleOptionButton()
                btn.initStyleOption(btn_opt)
                btn_opt.rect = self._get_button_rect(rect)
                btn_opt.text = '>' if self.is_collapsed(logical_index) else '<'
                if data['collapsed']:
                    opt.textAlignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
                    opt.text = name
            # Set the background colour for all the grouped column headers
            opt.palette.setColor(QtGui.QPalette.All, QtGui.QPalette.Button, data['colour'])

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

        # TODO: Should only modify the brush origin if a custom brush is given
        # for the current section
        old_brush_origin = painter.brushOrigin()
        painter.setBrushOrigin(opt.rect.topLeft())
        style.drawControl(QtWidgets.QStyle.CE_HeaderSection, opt, painter, self)
        style.drawControl(QtWidgets.QStyle.CE_HeaderLabel, opt, painter, self)
        painter.setBrushOrigin(old_brush_origin)

        if btn is not None:
            style.drawControl(QtWidgets.QStyle.CE_PushButton, btn_opt, painter, btn)

        painter.restore()

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

    def is_collapsed(self, logical_index):
        # type: (int) -> bool
        for data in self._groups.values():
            if logical_index in data['indexes']:
                return data['collapsed']
        return False

    def remove_group(self, name):
        # type: (str) -> bool
        removed = self.set_group_collapsed(name, False)
        self._groups.pop(name, None)
        return removed

    def set_collapsible_group(self, name, indexes, collapsed=False, colour=None):
        # type: (str, list[int], bool, QtGui.QColor) -> None
        # Ensure each index is only contained in one group
        for group_name, group_data in self._groups.items():
            overlap = set(group_data['indexes']) & set(indexes)
            if overlap:
                self._groups[group_name] = [i for i in indexes if i not in indexes]

        # Ensure all visual indexes are in order
        visuals = sorted(self.visualIndex(idx) for idx in indexes)
        logical = []
        minimum = visuals[0]
        for idx, visual_index in enumerate(visuals):
            ordered_visual_index = minimum + idx
            if visual_index != ordered_visual_index:
                self.moveSection(visual_index, ordered_visual_index)
            logical.append(self.logicalIndex(ordered_visual_index))

        self._groups[name] = {
            'colour': colour or QtGui.QColor('red'),
            'indexes': logical,
            'collapsed': collapsed,
            'width': self.sectionSize(logical[-1]),
        }

        # Expand / collapse if any of the indexes are collapsed
        self.set_group_collapsed(name, collapsed)

    def set_group_collapsed(self, name, collapsed):
        # type: (str, bool) -> bool
        data = self._groups.get(name)
        if not data:
            return False
        # Hide/Show all following indexes
        data['collapsed'] = collapsed
        indexes = data['indexes']
        last = indexes[-1]

        # Font metrics for the name
        if collapsed:
            # [ margin text margin btn margin ]
            opt = QtWidgets.QStyleOptionHeader()
            self.initStyleOption(opt)
            width = opt.fontMetrics.width(name)
            width += self.BTN_WIDTH + self.BTN_MARGIN * 3
            # Save the width before replacing it so it can be restored
            data['width'] = self.sectionSize(last)
        else:
            width = data['width']
        self.resizeSection(last, width)

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
        btn_width = min(self.BTN_WIDTH, section_rect.width() - self.BTN_MARGIN * 2)
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
                # else:
                #     return 'banana'
            elif role == QtCore.Qt.BackgroundRole:
                return QtGui.QColor('red')
            elif role == QtCore.Qt.ForegroundRole:
                return QtGui.QColor('blue')

        def index(self, row, column, parent=QtCore.QModelIndex()):
            # type: (int, int, QtCore.QModelIndex) -> QtCore.QModelIndex
            return self.createIndex(row, column, self._entities[row] if self._entities else None)

        def parent(self, child):
            # type: (QtCore.QModelIndex) -> QtCore.QModelIndex
            return QtCore.QModelIndex()

        def rowCount(self, parent=QtCore.QModelIndex()):
            # type: (QtCore.QModelIndex) -> int
            return len(self._entities)

        def setData(self, index, value, role=QtCore.Qt.EditRole):
            # type: (QtCore.QModelIndex, object, int) -> bool
            if not index.isValid():
                return False

    app = QtWidgets.QApplication(sys.argv)

    attrs = ('name', 'gender', 'age', 'race')
    Entity = namedtuple('Entity', attrs)

    model = EntityModel(attrs, [
        Entity('nuala', 'female', 30, 'human'),
        Entity('matthew', 'male', 30, 'human')
    ])
    view = QtWidgets.QTableView()
    header = HeaderView(QtCore.Qt.Horizontal, view)
    view.setHorizontalHeader(header)
    view.setModel(model)
    header.set_collapsible_group('Character', [0, 2, 3], collapsed=True)
    print(header._groups)
    view.show()

    app.exec_()
    sys.exit()
