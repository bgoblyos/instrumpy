import asyncio
import numpy as np
import plotly.graph_objects as go
from nicegui import app, ui
import sys
sys.path.append(r"../")

from Utilities.SetupLogging import setupLogging
logger = setupLogging()

from Devices.ARIS import ARIS

def get_plotly_spectral_colors(wavelengths, opacity=0.5):
    colors = []
    for wl in wavelengths:
        if wl < 380 or wl > 750:
            r, g, b = 0.3, 0.0, 0.0
        else:
            if 380 <= wl <= 440:
                r, g, b = -(wl - 440) / (440 - 380), 0.0, 1.0
            elif 440 < wl <= 490:
                r, g, b = 0.0, (wl - 440) / (490 - 440), 1.0
            elif 490 < wl <= 510:
                r, g, b = 0.0, 1.0, -(wl - 510) / (510 - 490)
            elif 510 < wl <= 580:
                r, g, b = (wl - 510) / (580 - 510), 1.0, 0.0
            elif 580 < wl <= 645:
                r, g, b = 1.0, -(wl - 645) / (645 - 580), 0.0
            else:
                r, g, b = 1.0, 0.0, 0.0

            if 380 <= wl <= 420:
                factor = 0.3 + 0.7 * (wl - 380) / (420 - 380)
            elif 420 < wl <= 700:
                factor = 1.0
            else:
                factor = 0.3 + 0.7 * (750 - wl) / (750 - 700)

            r, g, b = r * factor, g * factor, b * factor

        colors.append(f'rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, {opacity})')
    return colors

# -------------------------------------------------------------------
# 2. Device Lifecycle
# -------------------------------------------------------------------
device = None

def initialize_spectrometer():
    global device
    try:
        print('Connecting to ARIS...')
        device = ARIS() # Your actual imported device
        print('Connected.')
    except Exception as e:
        print(f'Init Failed: {e}')

app.on_startup(initialize_spectrometer)

# -------------------------------------------------------------------
# 3. Blazing Fast UI Logic & Hardware State
# -------------------------------------------------------------------
@ui.page('/')
def index_page():
    global device

    # --- State Tracking ---
    plot_ui = None
    fig = None
    settings_dirty = True  # Flag to trigger hardware setup

    # --- Hardware Configuration Handlers ---
    def flag_settings_changed():
        """Marks the hardware settings as out of date."""
        nonlocal settings_dirty
        settings_dirty = True

    def toggle_exposure_mode(e):
        """Enables/Disables manual inputs based on the auto-exposure checkbox."""
        if e.value: # Auto-exposure is ON
            exp_time_input.disable()
            avgs_input.disable()
        else:
            exp_time_input.enable()
            avgs_input.enable()
        flag_settings_changed()

    # --- Capture Loop ---
    async def capture_and_update():
        nonlocal plot_ui, fig, settings_dirty
        if device is None: return

        # 1. APPLY PENDING HARDWARE SETTINGS
        if settings_dirty:
            try:
                if auto_exp_box.value:
                    update_timer.interval = (tgt_time_input.value * 2)/1e3
                    device.setAutoExposure(tgt_time_input.value*1000)
                print(f"Applying new settings -> Auto: {auto_exp_box.value}, Exp: {exp_time_input.value}ms, Avgs: {avgs_input.value}")

                settings_dirty = False
            except Exception as e:
                ui.notify(f"Hardware Setup Error: {e}", type='negative')
                return

        # 2. CAPTURE DATA
        try:
            res = device.capture()
            x = np.array(res['wavelengths'])
            y = np.array(res['spectrum'])

            # --- TELEMETRY UPDATE ---
            # Fetch load level, exposure, and averages from the device payload.
            # Using .get() with fallbacks prevents errors if the device doesn't return them immediately.
            load_val = res.get('load_level', 0)
            load_pct = int(load_val * 100)
            actual_exp = res.get('exposure_us', 0)/1000
            actual_avgs = res.get('averaging', 0)

            # Update telemetry labels
            load_gauge.value = load_pct
            load_label.text = '' #f'{load_pct}%'
            exp_feedback.text = f'Exp: {actual_exp} ms'
            avg_feedback.text = f'Avg: {actual_avgs}'

            # Gauge color logic
            if load_pct < 50:
                load_gauge.props('color=green')
            elif load_pct < 85:
                load_gauge.props('color=orange')
            else:
                load_gauge.props('color=red')

            # --- PLOT UPDATE ---
            if fig is None:
                point_colors = get_plotly_spectral_colors(x, opacity=0.6)

                widths = np.diff(x)
                widths = np.append(widths, widths[-1]) * 1.05

                fig = go.Figure()

                fig.add_trace(go.Bar(
                    x=x, y=y,
                    width=widths,
                    marker_color=point_colors,
                    marker_line_width=0,
                    name='Fill'
                ))

                fig.add_trace(go.Scatter(
                    x=x, y=y,
                    mode='lines',
                    line=dict(color='black', width=1.5),
                    name='Signal'
                ))

                fig.update_layout(
                    title='ARIS Live Spectrum',
                    xaxis_title='Wavelength (nm)',
                    yaxis_title='Intensity (a.u.)',
                    showlegend=False,
                    template='plotly_white',
                    bargap=0,
                    bargroupgap=0,
                    uirevision='constant',
                    margin=dict(l=60, r=40, t=60, b=60),
                    font=dict(family="Arial, Helvetica, sans-serif", size=14, color="#333333"),
                    yaxis=dict(title_font=dict(size=16), tickfont=dict(size=12)),
                    xaxis=dict(title_font=dict(size=16), tickfont=dict(size=12))
                )

                with plot_container:
                    plot_ui = ui.plotly(fig).classes('w-full h-96')
                    plot_ui.update_config({'toImageButtonOptions': {'format': 'svg'}})
                    loading_label.set_visibility(False)

            else:
                fig.data[0].y = y
                fig.data[1].y = y
                plot_ui.update()

        except Exception as e:
            ui.notify(f"Capture Error: {e}", type='negative')
            if update_timer.active:
                toggle_continuous()

    def toggle_continuous():
        if update_timer.active:
            update_timer.deactivate()
            continuous_btn.text = 'Start Continuous'
            continuous_btn.props('color=positive')
            capture_btn.enable()
        else:
            update_timer.activate()
            continuous_btn.text = 'Stop Continuous'
            continuous_btn.props('color=negative')
            capture_btn.disable()

    # --- UI Layout ---
    # Top Header & Telemetry Dashboard
    with ui.row().classes('w-full items-center justify-between mb-4'):
        ui.label('Spectral Visualization Dashboard').classes('text-2xl font-bold')

        with ui.row().classes('items-center gap-6 bg-white px-5 py-2 rounded shadow-sm border'):

            # Telemetry Feedback
            with ui.column().classes('gap-0 text-right'):
                ui.label('LIVE TELEMETRY').classes('text-[10px] text-gray-400 font-bold tracking-widest')
                exp_feedback = ui.label('Exp: -- ms').classes('text-sm font-mono font-bold text-gray-700')
                avg_feedback = ui.label('Avg: --').classes('text-sm font-mono font-bold text-gray-700')

            # Vertical Divider
            ui.separator().props('vertical')

            # Load Gauge
            with ui.row().classes('items-center gap-3'):
                ui.label('LOAD').classes('text-sm text-gray-600 font-bold tracking-wide uppercase')
                with ui.circular_progress(value=0, min=0, max=100, color='green') \
                    .props('size=3rem thickness=0.25 track-color=grey-3') as load_gauge:
                    load_label = ui.label('0%').classes('text-xs font-bold text-gray-800')

    # Main Plot Container
    with ui.card().classes('w-full items-center bg-gray-50') as plot_container:
        loading_label = ui.label('Awaiting initial data from spectrometer...').classes('text-gray-500 py-10')

    # Hardware Controls & Actions
    with ui.row().classes('w-full justify-between items-center mt-4 bg-white p-4 rounded shadow-sm border'):

        # Spectrometer Settings
        with ui.row().classes('items-center gap-6'):
            ui.label('Settings:').classes('font-bold text-gray-700')
            auto_exp_box = ui.checkbox('Auto-Exposure', value = True, on_change=toggle_exposure_mode)

            tgt_time_input = ui.number('Target time (ms)', value=200, min=0.1, step=1, on_change=flag_settings_changed).classes('w-32')

            ui.label('Manual exposure:').classes('font-regular text-gray-700')
            exp_time_input = ui.number('Exposure (ms)', value=10, min=1, step=1, on_change=flag_settings_changed) \
                .classes('w-32')

            avgs_input = ui.number('Averages', value=1, min=1, step=1, on_change=flag_settings_changed) \
                .classes('w-24')

            exp_time_input.disable()
            avgs_input.disable()
        # Actions
        with ui.row().classes('gap-4'):
            capture_btn = ui.button('Capture Single', on_click=capture_and_update, color='primary')
            continuous_btn = ui.button('Start Continuous', on_click=toggle_continuous, color='positive')

    update_timer = ui.timer(0.04, capture_and_update, active=False)

ui.run(title='ARIS Spectral Visualization')
