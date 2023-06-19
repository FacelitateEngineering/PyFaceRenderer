"""."""

import dearpygui.dearpygui as dpg

# thing user last clicked
global currentPick
currentPick = None

# thing mouse last hovered
global currentSelection
currentSelection = None

class Sprite():
    def __init__(self, path=None, width=128, height=128, data=None):
        # loading an image overrides any other parameters
        if path:
            _width, _height, _chan, _data = dpg.load_image(path)
        else:
            _width = width
            _height = height
            _chan = 4
            # default block of black
            _data = data or [0, 0, 0, 1] * _width * _height
        self.__imageList = {}
        with dpg.texture_registry(show=False):
            self.__id = dpg.add_dynamic_texture(_width, _height, _data)
        self.__path = path
        self.__data = _data
        self.__width = _width
        self.__height = _height
        self.__chan = _chan

    def __str__(self):
        return f"{self.__path} {self.__width}x{self.__height}x{self.__chan}"

    @property
    def id(self):
        return self.__id

    @property
    def entry(self):
        return self.__width, self.__height, self.__data

    @property
    def data(self):
        return self.__data

    def contains(self, px, py, canvas=None):
        # if canvas is none, iterate the stack
        if canvas is None:
            container = sum(self.__imageList.values(), [])
        else:
            container = self.__imageList.get(str(canvas), [])

        for item in container:
            pos = dpg.get_item_configuration(item)
            if pos['pmin'][0] <= px <= pos['pmax'][0] and pos['pmin'][1] <= py <= pos['pmax'][1]:
                return item
        return None

    def draw(self, canvas, x=0, y=0, width=None, height=None):
        w = width or self.__width
        h = height or self.__height
        image = dpg.draw_image(self.__id, pmin=[x, y], pmax=[x + w, y + h], parent=canvas)
        key = str(canvas)
        data = self.__imageList.get(key, [])
        data.append(image)
        self.__imageList[key] = data

    def __del__(self):
        for x in self.__imageList:
            try:
                dpg.delete_item(x)
            except Exception as _:
                ...

def mouseInRect(drawlist, canvas=None):
	px, py = dpg.get_mouse_pos(local=False)
	for item in drawlist:
		if (drawable := item.contains(px, py, canvas=canvas)) is not None:
			return drawable
	return None

def mouseClick(x_coord_entry, canvas):
	px, py = dpg.get_mouse_pos(local=False)
	if px < 200:
		return

	global currentSelection
	global currentPick
	if currentSelection is None:
		if currentPick is not None:
			dpg.delete_item(currentPick)
		currentPick = None
		return

	selected = dpg.get_item_user_data(currentSelection)
	config = dpg.get_item_configuration(selected)
	pmin = [config['pmin'][0] - 2, config['pmin'][1] - 2]
	pmax = [config['pmax'][0] + 2, config['pmax'][1] + 2]
	dpg.set_value(x_coord_entry, config['pmin'][0])

	if currentPick is None:
		currentPick = dpg.draw_rectangle(pmin, pmax, thickness=2, parent=canvas, color=[255, 0, 0, 255], user_data=selected)

	if dpg.get_item_user_data(currentPick) != selected:
		dpg.configure_item(currentPick, pmin=pmin, pmax=pmax, user_data=selected)

def mouseMove(drawlist, canvas):
	global currentSelection
	if (selected := mouseInRect(drawlist, canvas)) is None:
		if currentSelection is not None:
			dpg.delete_item(currentSelection)
		currentSelection = None
		return

	config = dpg.get_item_configuration(selected)
	pmin = [config['pmin'][0] - 2, config['pmin'][1] - 2]
	pmax = [config['pmax'][0] + 2, config['pmax'][1] + 2]

	if currentSelection is None:
		currentSelection = dpg.draw_rectangle(pmin, pmax, thickness=2, parent=canvas, user_data=selected)

	if dpg.get_item_user_data(currentSelection) != selected:
		dpg.configure_item(currentSelection, pmin=pmin, pmax=pmax, user_data=selected)

def mouseDrag():
	global currentPick
	if currentPick is None:
		return

	px, py = dpg.get_mouse_pos(local=False)
	if px < 200:
		return

	selected = dpg.get_item_user_data(currentPick)
	config = dpg.get_item_configuration(selected)
	pmin = [px, py]
	w = config['pmax'][0] - config['pmin'][0]
	h = config['pmax'][1] - config['pmin'][1]
	pmax = [px + w, py + h]
	dpg.configure_item(selected, pmin=pmin, pmax=pmax)
	dpg.configure_item(currentPick, pmin=pmin, pmax=pmax)

def set_height(properties):
	height = dpg.get_viewport_height()
	dpg.configure_item(properties, height=height)

def x_coord_entry_handler(sender, value, user):
	global currentPick
	if currentPick is None:
		return

	selected = dpg.get_item_user_data(currentPick)
	config = dpg.get_item_configuration(selected)
	pmin = [value, config['pmin'][1]]
	value -= config['pmin'][0]
	pmax = [config['pmax'][0] + value, config['pmax'][1]]
	dpg.configure_item(selected, pmin=pmin, pmax=pmax)
	dpg.configure_item(currentPick, pmin=pmin, pmax=pmax)

def init():
	# dpg.setup_registries()

    dpg.create_viewport(title=f'DearPyGui Drag test', width=1920, height=1080, always_on_top=False, )
    with dpg.window(width=200, no_title_bar=True, pos=[0, 0], no_resize=True, no_move=True) as properties:
        x_coord_entry = dpg.add_input_int(max_value=1000, callback=x_coord_entry_handler)

    canvas = dpg.add_viewport_drawlist(front=True)
    image = Sprite("examples/models/fuze_uv.jpg")
    image.draw(canvas, x=350, y=100, width=150, height=150)
    image.draw(canvas, x=550, y=100, width=150, height=150)
    drawlist = [image]

    dpg.setup_dearpygui()
    dpg.show_viewport()
    with dpg.handler_registry():
        dpg.add_mouse_click_handler(callback=lambda s, d: mouseClick(x_coord_entry, canvas,))
        dpg.add_mouse_move_handler(callback=lambda s, d: mouseMove(drawlist, canvas,))
        dpg.add_mouse_drag_handler(callback=lambda s, d: mouseDrag())

    dpg.set_viewport_resize_callback(lambda s, d: set_height(properties))
    

if __name__ == '__main__':
    dpg.create_context()
    dpg.configure_app(docking=True, docking_space=True, )
    init()
    dpg.start_dearpygui()