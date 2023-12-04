
import dearpygui.dearpygui as dpg
import numpy as np

dpg.create_context()

with dpg.window(width=500, height=300):
    dpg.add_text("Click me with any mouse button", tag="text item")
    dpg.add_text("Close window with arrow to change visible state printing to console", tag="text item 2")
    with dpg.group(horizontal=True):
        dpg.add_drag_doublex(size=4, callback=lambda s, a, u: print(f'Double: {a}'), tag='drag_double')
        dpg.add_button(label='Set Double to 1', callback=lambda: dpg.set_value('drag_double', [1.0,] * 4))
        dpg.add_button(label='Set Double to random', callback=lambda: dpg.set_value('drag_double', np.random.randn(4).astype(np.float32)))

    with dpg.group(horizontal=True):
        dpg.add_drag_floatx(size=4, callback=lambda s, a, u: print(f'Float: {a}'), tag='drag_float')
        dpg.add_button(label='Set float to 1', callback=lambda: dpg.set_value('drag_float', [1.0,] * 4))
        dpg.add_button(label='Set float to random', callback=lambda: dpg.set_value('drag_float', np.random.randn(4).astype(np.float32)))



dpg.create_viewport(title='Test Drag', width=800, height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()