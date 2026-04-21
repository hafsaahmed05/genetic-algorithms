import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import copy
import queue
import csv
import os
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

from config import (ACTIVITIES, ROOMS, TIMES, FACILITATORS,
                    format_time, generate_initial_population)
from fitness import calculate_fitness

os.makedirs('results', exist_ok=True)

# ── Colours — Tea Garden palette ─────────────────────────────────────────────
BG       = "#f4ede8"       # blush white (main background)
PANEL    = "#ffffff"       # clean white panels
ACCENT   = "#769281"       # sage green (primary accent)
ACCENT2  = "#ecb783"       # warm terracotta (warning/stop)
ACCENT3  = "#7d90bc"       # slate blue-grey (secondary)
TEXT     = "#4a4a4a"       # soft charcoal
SUBTEXT  = "#433e37"       # warm grey
BORDER   = "#dce1da"       # pale sage border

# ── Helpers ───────────────────────────────────────────────────────────────────
def softmax(arr):
    a = np.array(arr, dtype=float)
    e = np.exp(a - np.max(a))
    return e / e.sum()

def crossover(p1, p2, rng):
    return {act: copy.deepcopy(p1[act] if rng.random() < 0.5 else p2[act])
            for act in p1}

def mutate(child, rate, rng):
    for act in child:
        if rng.random() < rate:
            feat = rng.choice(['room', 'time', 'fac'])
            if feat == 'room':  child[act]['room'] = str(rng.choice(list(ROOMS)))
            elif feat == 'time': child[act]['time'] = int(rng.choice(TIMES))
            else:               child[act]['fac']  = str(rng.choice(FACILITATORS))
    return child

def count_violations(schedule):
    room_time = {}
    fac_load  = {f: 0 for f in FACILITATORS}
    room_size_v = 0
    special_v   = 0

    for act, d in schedule.items():
        rt = (d['room'], d['time'])
        room_time[rt] = room_time.get(rt, []) + [act]
        fac_load[d['fac']] += 1
        cap = ROOMS[d['room']]
        enr = ACTIVITIES[act]['enrollment']
        if cap < enr or cap > 3 * enr:
            room_size_v += 1

    room_conflicts = sum(len(v) - 1 for v in room_time.values() if len(v) > 1)
    fac_overload   = sum(1 for f, l in fac_load.items() if l > 4)

    # SLA 101 same slot
    if (schedule['SLA101A']['time'] == schedule['SLA101B']['time']):
        special_v += 1
    if (schedule['SLA191A']['time'] == schedule['SLA191B']['time']):
        special_v += 1

    return room_conflicts, fac_overload, room_size_v, special_v


# ── Evolution worker (runs in a thread) ──────────────────────────────────────
class EvolutionWorker:
    def __init__(self, pop_size, init_mr, q, stop_event):
        self.pop_size   = pop_size
        self.init_mr    = init_mr
        self.q          = q          # queue to send updates to GUI
        self.stop_event = stop_event
        self.rng        = np.random.default_rng()

    def run(self):
        rng = self.rng
        pop = generate_initial_population(self.pop_size)
        mr  = self.init_mr

        h_best, h_avg, h_worst = [], [], []
        prev_avg      = None
        plateau_count = 0
        mr_halves     = 0
        gen           = 0

        log_path = f"results/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_f    = open(log_path, 'w', newline='')
        log_w    = csv.writer(log_f)
        log_w.writerow(['Timestamp','Generation','Best','Average','Worst','Improvement%','MutationRate'])

        while not self.stop_event.is_set():
            gen += 1
            fits    = [calculate_fitness(ind) for ind in pop]
            best_f  = max(fits)
            worst_f = min(fits)
            avg_f   = sum(fits) / len(pop)

            h_best.append(best_f);  h_avg.append(avg_f);  h_worst.append(worst_f)

            imp = 0.0
            if prev_avg is not None and prev_avg != 0:
                imp = (avg_f - prev_avg) / abs(prev_avg)

            log_w.writerow([datetime.now().isoformat(), gen,
                            round(best_f,4), round(avg_f,4), round(worst_f,4),
                            round(imp*100,4), round(mr,6)])

            best_idx  = fits.index(best_f)
            best_sched = pop[best_idx]
            rc, fo, rsv, sv = count_violations(best_sched)

            self.q.put({
                'gen': gen, 'best': best_f, 'avg': avg_f, 'worst': worst_f,
                'imp': imp*100, 'mr': mr,
                'h_best': h_best[:], 'h_avg': h_avg[:], 'h_worst': h_worst[:],
                'schedule': best_sched,
                'violations': (rc, fo, rsv, sv),
                'fac_load': {f: sum(1 for d in best_sched.values() if d['fac']==f)
                             for f in FACILITATORS},
                'room_util': {r: sum(1 for d in best_sched.values() if d['room']==r)
                              for r in ROOMS},
            })

            # plateau / halving
            if prev_avg is not None and imp < 0.01:
                plateau_count += 1
            else:
                plateau_count = 0

            if plateau_count >= 5:
                mr /= 2.0;  mr_halves += 1;  plateau_count = 0

            # stopping
            if gen >= 100:
                if mr_halves >= 5 and imp <= 0.01:
                    break
                if plateau_count >= 10:
                    break

            prev_avg = avg_f

            # next gen
            next_gen = [copy.deepcopy(best_sched)]
            probs    = softmax(fits)
            while len(next_gen) < self.pop_size:
                i1, i2 = rng.choice(len(pop), size=2, p=probs, replace=False)
                child = crossover(pop[i1], pop[i2], rng)
                child = mutate(child, mr, rng)
                next_gen.append(child)
            pop = next_gen

        log_f.close()

        # write final schedule
        best_idx   = fits.index(max(fits))
        best_sched = pop[best_idx]
        with open('results/best_schedule.txt', 'w') as f:
            f.write("FINAL OPTIMAL SCHEDULE\n" + "="*60 + "\n")
            for act in sorted(best_sched):
                d = best_sched[act]
                f.write(f"{act:8s} | Room: {d['room']:11s} | Time: {format_time(d['time']):6s} | Fac: {d['fac']}\n")

        with open('results/fitness_history.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Generation','Best','Average','Worst'])
            for i,(b,a,wo) in enumerate(zip(h_best,h_avg,h_worst),1):
                w.writerow([i,b,a,wo])

        self.q.put({'done': True, 'final_fitness': max(fits)})


# ── Main GUI ──────────────────────────────────────────────────────────────────
class SchedulerGUI:
    def __init__(self, root):
        self.root       = root
        self.root.title("SLA Genetic Scheduler")
        self.root.configure(bg=BG)
        self.root.geometry("1400x860")
        self.root.minsize(1100, 700)

        self.q          = queue.Queue()
        self.stop_event = threading.Event()
        self.worker     = None
        self.running    = False

        self._build_ui()
        self._poll_queue()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self.stop_event.set()
        if hasattr(self, '_after_id'):
            self.root.after_cancel(self._after_id)
        self.root.destroy()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self):
        sb = tk.Frame(self.root, bg=PANEL, width=240)
        sb.grid(row=0, column=0, sticky='nsew')
        sb.grid_propagate(False)

        # Title
        tk.Label(sb, text="⬡ SLA", font=("Courier New", 22, "bold"),
                 fg=ACCENT, bg=PANEL).pack(pady=(24,2))
        tk.Label(sb, text="Genetic Scheduler", font=("Courier New", 11),
                 fg=SUBTEXT, bg=PANEL).pack()

        ttk.Separator(sb, orient='horizontal').pack(fill='x', padx=16, pady=20)

        # Controls
        def label(txt):
            tk.Label(sb, text=txt, font=("Courier New", 10, "bold"),
                     fg=SUBTEXT, bg=PANEL).pack(anchor='w', padx=20, pady=(8,1))

        label("POPULATION SIZE")
        self.pop_var = tk.IntVar(value=500)
        self._slider(sb, self.pop_var, 100, 1000, 50)

        label("INITIAL MUTATION RATE")
        self.mr_var = tk.DoubleVar(value=0.01)
        self._slider(sb, self.mr_var, 0.001, 0.1, 0.001)

        ttk.Separator(sb, orient='horizontal').pack(fill='x', padx=16, pady=20)

        # Status indicators
        self._stat(sb, "GENERATION", "gen_lbl", "—")
        self._stat(sb, "BEST FITNESS", "best_lbl", "—")
        self._stat(sb, "AVG FITNESS",  "avg_lbl",  "—")
        self._stat(sb, "MUTATION RATE","mr_lbl",   "—")
        self._stat(sb, "IMPROVEMENT",  "imp_lbl",  "—")

        ttk.Separator(sb, orient='horizontal').pack(fill='x', padx=16, pady=20)

        # Buttons
        self.run_btn = tk.Button(sb, text="▶  RUN",
                                 command=self._start,
                                 font=("Courier New", 11, "bold"),
                                 bg=ACCENT, fg="white", relief='flat',
                                 activebackground="#3a6a8a", cursor='hand2',
                                 pady=10)
        self.run_btn.pack(fill='x', padx=20, pady=4)

        self.stop_btn = tk.Button(sb, text="■  STOP",
                                  command=self._stop,
                                  font=("Courier New", 11, "bold"),
                                  bg=ACCENT2, fg="white", relief='flat',
                                  activebackground="#e8809a", cursor='hand2',
                                  state='disabled', pady=10)
        self.stop_btn.pack(fill='x', padx=20, pady=4)

        tk.Button(sb, text="⟳  RESET",
                  command=self._reset,
                  font=("Courier New", 10),
                  bg=BORDER, fg=TEXT, relief='flat',
                  cursor='hand2', pady=8).pack(fill='x', padx=20, pady=4)

        tk.Button(sb, text="✕  CLOSE",
                  command=self._on_close,
                  font=("Courier New", 10),
                  bg=ACCENT3, fg="white", relief='flat',
                  cursor='hand2', pady=8).pack(fill='x', padx=20, pady=4)

    def _slider(self, parent, var, lo, hi, res):
        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill='x', padx=20)
        val_lbl = tk.Label(f, textvariable=var, font=("Courier New", 11, "bold"),
                           fg=ACCENT, bg=PANEL, width=6, anchor='e')
        val_lbl.pack(side='right')
        tk.Scale(f, variable=var, from_=lo, to=hi, resolution=res,
                 orient='horizontal', bg=PANEL, fg=TEXT,
                 troughcolor=BORDER, highlightthickness=0,
                 sliderrelief='flat', showvalue=False).pack(side='left', fill='x', expand=True)

    def _stat(self, parent, label, attr, val):
        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill='x', padx=20, pady=2)
        tk.Label(f, text=label, font=("Courier New", 9), fg=SUBTEXT, bg=PANEL).pack(anchor='w')
        lbl = tk.Label(f, text=val, font=("Courier New", 15, "bold"), fg=ACCENT, bg=PANEL)
        lbl.pack(anchor='w')
        setattr(self, attr, lbl)

    def _build_main(self):
        main = tk.Frame(self.root, bg=BG)
        main.grid(row=0, column=1, sticky='nsew', padx=12, pady=12)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=3)
        main.rowconfigure(1, weight=2)

        # ── Top: notebook with charts ─────────────────────────────────────────
        nb = ttk.Notebook(main)
        nb.grid(row=0, column=0, sticky='nsew', pady=(0,8))

        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook',        background=BG,    borderwidth=0)
        style.configure('TNotebook.Tab',    background=BORDER, foreground=TEXT,
                        font=('Courier New', 10), padding=[14,7])
        style.map('TNotebook.Tab',          background=[('selected', PANEL)])

        # Tab 1 – fitness plot
        self.fig_fit, self.ax_fit = plt.subplots(facecolor=BG)
        self.ax_fit.set_facecolor(PANEL)
        self._style_ax(self.ax_fit, "Fitness over Generations", "Generation", "Fitness")
        self.line_best,  = self.ax_fit.plot([], [], color=ACCENT,  lw=2, label='Best')
        self.line_avg,   = self.ax_fit.plot([], [], color=ACCENT3, lw=2, label='Average')
        self.line_worst, = self.ax_fit.plot([], [], color=ACCENT2, lw=2, label='Worst')
        self.ax_fit.legend(facecolor=PANEL, edgecolor=BORDER,
                           labelcolor=TEXT, fontsize=8)
        canvas_fit = FigureCanvasTkAgg(self.fig_fit, master=nb)
        nb.add(canvas_fit.get_tk_widget(), text='  📈 Fitness  ')
        self.canvas_fit = canvas_fit

        # Tab 2 – bar chart: facilitator load
        self.fig_bar, self.ax_bar = plt.subplots(facecolor=BG)
        self.ax_bar.set_facecolor(PANEL)
        self._style_ax(self.ax_bar, "Facilitator Course Load", "Facilitator", "# Activities")
        canvas_bar = FigureCanvasTkAgg(self.fig_bar, master=nb)
        nb.add(canvas_bar.get_tk_widget(), text='  📊 Load  ')
        self.canvas_bar = canvas_bar

        # Tab 3 – pie: room utilization
        self.fig_pie, self.ax_pie = plt.subplots(facecolor=BG)
        self.ax_pie.set_facecolor(BG)
        canvas_pie = FigureCanvasTkAgg(self.fig_pie, master=nb)
        nb.add(canvas_pie.get_tk_widget(), text='  🥧 Rooms  ')
        self.canvas_pie = canvas_pie

        # Tab 4 – violations pie
        self.fig_vio, self.ax_vio = plt.subplots(facecolor=BG)
        self.ax_vio.set_facecolor(BG)
        canvas_vio = FigureCanvasTkAgg(self.fig_vio, master=nb)
        nb.add(canvas_vio.get_tk_widget(), text='  ⚠️ Violations  ')
        self.canvas_vio = canvas_vio

        # ── Bottom: schedule table ────────────────────────────────────────────
        bottom = tk.Frame(main, bg=BG)
        bottom.grid(row=1, column=0, sticky='nsew')
        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(0, weight=1)

        tk.Label(bottom, text="BEST SCHEDULE", font=("Courier New", 9),
                 fg=SUBTEXT, bg=BG).grid(row=0, column=0, sticky='w', pady=(0,4))

        cols = ('Activity', 'Room', 'Time', 'Facilitator')
        self.tree = ttk.Treeview(bottom, columns=cols, show='headings', height=8)
        style.configure('Treeview', background=PANEL, foreground=TEXT,
                        fieldbackground=PANEL, font=('Courier New', 10),
                        rowheight=26)
        style.configure('Treeview.Heading', background=BORDER, foreground=ACCENT3,
                        font=('Courier New', 10, 'bold'))
        style.map('Treeview', background=[('selected', BORDER)])

        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=160, anchor='center')
        self.tree.grid(row=1, column=0, sticky='nsew')

        sb_tree = ttk.Scrollbar(bottom, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb_tree.set)
        sb_tree.grid(row=1, column=1, sticky='ns')

    def _style_ax(self, ax, title, xlabel, ylabel):
        ax.set_title(title, color=TEXT, fontsize=10, fontfamily='monospace', pad=8)
        ax.set_xlabel(xlabel, color=SUBTEXT, fontsize=8, fontfamily='monospace')
        ax.set_ylabel(ylabel, color=SUBTEXT, fontsize=8, fontfamily='monospace')
        ax.tick_params(colors=SUBTEXT, labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)
        ax.grid(color=BORDER, linewidth=0.5, alpha=0.6)

    # ── Controls ──────────────────────────────────────────────────────────────
    def _start(self):
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.run_btn.config(state='disabled')
        self.stop_btn.config(state='normal')

        self.worker = EvolutionWorker(
            pop_size  = self.pop_var.get(),
            init_mr   = self.mr_var.get(),
            q         = self.q,
            stop_event= self.stop_event,
        )
        threading.Thread(target=self.worker.run, daemon=True).start()

    def _stop(self):
        self.stop_event.set()
        self.run_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.running = False

    def _reset(self):
        self._stop()
        # clear plots
        self.line_best.set_data([], [])
        self.line_avg.set_data([], [])
        self.line_worst.set_data([], [])
        self.ax_fit.relim(); self.ax_fit.autoscale_view()
        self.canvas_fit.draw()
        self.ax_bar.cla(); self._style_ax(self.ax_bar,"Facilitator Course Load","Facilitator","# Activities")
        self.canvas_bar.draw()
        self.ax_pie.cla(); self.canvas_pie.draw()
        self.ax_vio.cla(); self.canvas_vio.draw()
        for row in self.tree.get_children():
            self.tree.delete(row)
        for attr in ('gen_lbl','best_lbl','avg_lbl','mr_lbl','imp_lbl'):
            getattr(self, attr).config(text='—')

    # ── Queue polling ─────────────────────────────────────────────────────────
    def _poll_queue(self):
        try:
            while True:
                data = self.q.get_nowait()
                if data.get('done'):
                    self._on_done(data)
                else:
                    self._update(data)
        except queue.Empty:
            pass
        self._after_id = self.root.after(100, self._poll_queue)

    def _on_done(self, data):
        self.running = False
        self.run_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.gen_lbl.config(text="DONE", fg=ACCENT)

    def _update(self, d):
        # sidebar stats
        self.gen_lbl.config(text=str(d['gen']))
        self.best_lbl.config(text=f"{d['best']:.3f}")
        self.avg_lbl.config(text=f"{d['avg']:.3f}")
        self.mr_lbl.config(text=f"{d['mr']:.6f}")
        color = ACCENT if d['imp'] >= 0 else ACCENT2
        self.imp_lbl.config(text=f"{d['imp']:+.3f}%", fg=color)

        gens = list(range(1, len(d['h_best']) + 1))

        # ── fitness line chart ────────────────────────────────────────────────
        self.line_best.set_data(gens, d['h_best'])
        self.line_avg.set_data(gens, d['h_avg'])
        self.line_worst.set_data(gens, d['h_worst'])
        self.ax_fit.relim(); self.ax_fit.autoscale_view()
        self.canvas_fit.draw()

        # ── bar: facilitator load ─────────────────────────────────────────────
        self.ax_bar.cla()
        self._style_ax(self.ax_bar, "Facilitator Course Load", "Facilitator", "# Activities")
        facs = list(d['fac_load'].keys())
        vals = list(d['fac_load'].values())
        colors = [ACCENT if v >= 3 else ACCENT2 if v == 0 else ACCENT3 for v in vals]
        bars = self.ax_bar.bar(facs, vals, color=colors, edgecolor=BORDER, linewidth=0.5)
        self.ax_bar.set_xticks(range(len(facs)))
        self.ax_bar.set_xticklabels(facs, rotation=35, ha='right', fontsize=7, color=SUBTEXT)
        for bar, v in zip(bars, vals):
            self.ax_bar.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                             str(v), ha='center', va='bottom', fontsize=7, color=TEXT)
        self.canvas_bar.draw()

        # ── pie: room utilization ─────────────────────────────────────────────
        self.ax_pie.cla()
        self.ax_pie.set_facecolor(BG)
        util = {r: v for r, v in d['room_util'].items() if v > 0}
        if util:
            pie_colors = plt.cm.Set2(np.linspace(0, 1, len(util)))
            wedges, texts, autotexts = self.ax_pie.pie(
                util.values(), labels=util.keys(),
                autopct='%1.0f%%', colors=pie_colors,
                textprops={'color': TEXT, 'fontsize': 7},
                wedgeprops={'edgecolor': BG, 'linewidth': 1.5}
            )
            for at in autotexts:
                at.set_fontsize(7); at.set_color(BG)
        self.ax_pie.set_title("Room Utilization", color=TEXT, fontsize=10,
                              fontfamily='monospace', pad=8)
        self.canvas_pie.draw()

        # ── pie: violations ───────────────────────────────────────────────────
        self.ax_vio.cla()
        self.ax_vio.set_facecolor(BG)
        rc, fo, rsv, sv = d['violations']
        vio_labels = ['Room\nConflicts', 'Fac\nOverload', 'Room Size\nViolations', 'Special\nRule']
        vio_vals   = [rc, fo, rsv, sv]
        if sum(vio_vals) == 0:
            self.ax_vio.text(0.5, 0.5, '✓ No Violations', ha='center', va='center',
                             fontsize=14, color=ACCENT, fontfamily='monospace',
                             transform=self.ax_vio.transAxes)
        else:
            vio_colors = [ACCENT2, ACCENT3, "#c8b8a2", ACCENT]
            nz = [(l,v,c) for l,v,c in zip(vio_labels,vio_vals,vio_colors) if v > 0]
            self.ax_vio.pie([x[1] for x in nz], labels=[x[0] for x in nz],
                            colors=[x[2] for x in nz], autopct='%1.0f%%',
                            textprops={'color': TEXT, 'fontsize': 7},
                            wedgeprops={'edgecolor': BG, 'linewidth': 1.5})
        self.ax_vio.set_title("Constraint Violations", color=TEXT, fontsize=10,
                              fontfamily='monospace', pad=8)
        self.canvas_vio.draw()

        # ── schedule table ────────────────────────────────────────────────────
        for row in self.tree.get_children():
            self.tree.delete(row)
        sched = d['schedule']
        for act in sorted(sched):
            dd = sched[act]
            tag = 'pref' if dd['fac'] in ACTIVITIES[act]['pref'] else \
                  'other' if dd['fac'] in ACTIVITIES[act]['other'] else 'none'
            self.tree.insert('', 'end',
                             values=(act, dd['room'], format_time(dd['time']), dd['fac']),
                             tags=(tag,))
        self.tree.tag_configure('pref',  foreground=ACCENT)
        self.tree.tag_configure('other', foreground=ACCENT3)
        self.tree.tag_configure('none',  foreground=ACCENT2)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    app  = SchedulerGUI(root)
    root.mainloop()