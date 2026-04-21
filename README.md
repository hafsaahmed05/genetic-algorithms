# SLA Genetic Algorithm Scheduler

**CS 461 – AI Program 2**

This project implements a **genetic algorithm (GA)** to generate an optimized activity schedule for the Seminar Learning Association (SLA). The algorithm assigns each activity a **room, time slot, and facilitator** while maximizing a fitness function based on multiple constraints.

---

## Quick Start

```bash
# Install dependencies
pip install numpy matplotlib

# Run CLI version
python main.py

# Run GUI version (bonus)
python main.py --gui
```

---

## Project Structure

```
genetic-algorithms/
├── main.py          # Entry point (CLI + GUI toggle)
├── config.py        # Data definitions (activities, rooms, etc.)
├── fitness.py       # Fitness function
├── evolution.py     # Genetic algorithm logic
├── gui.py           # Interactive visualization (Tkinter)
├── results/         # Output files
│   ├── best_schedule.txt
│   ├── fitness_history.csv
│   ├── fitness_plot.png
│   └── run_*.log
└── README.md
```

---

## How the Genetic Algorithm Works

### 1. Initialization

* A population of **500 random schedules** is generated.
* Each schedule randomly assigns:

  * Room
  * Time
  * Facilitator


### 2. Fitness Function

Each schedule is scored based on constraints:

| Category                    | Description           | Score |
| --------------------------- | --------------------- | ----- |
| Room conflicts              | Same room + same time | -0.5  |
| Room size too small         | Capacity < enrollment | -0.5  |
| Room too large (>3x)        | Wasteful space        | -0.4  |
| Room slightly large (>1.5x) | Minor waste           | -0.2  |
| Good room fit               | Efficient usage       | +0.3  |
| Preferred facilitator       | Ideal assignment      | +0.5  |
| Acceptable facilitator      | Valid assignment      | +0.2  |
| Incorrect facilitator       | Undesirable           | -0.1  |
| Single facilitator per slot | Good distribution     | +0.2  |
| Double-booked facilitator   | Conflict              | -0.2  |
| Overloaded facilitator (>4) | Too many tasks        | -0.5  |
| Underloaded (<3)            | Underutilized         | -0.4  |

Additional rules apply for SLA 101 / 191 scheduling relationships.


### 3. Selection (Softmax)

* Fitness values are converted into probabilities using the **softmax algorithm**
* Higher fitness → higher chance of selection
* Prevents premature domination by one solution


### 4. Crossover

* **Uniform crossover**
* Each activity is inherited randomly from either parent (50/50)


### 5. Mutation

* Initial mutation rate: **0.01 (1%)**
* Randomly mutates:
  * Room OR
  * Time OR
  * Facilitator


### 6. Adaptive Mutation Rate

* If improvement < 1% for **5 consecutive generations**, mutation rate is **halved**

* Enables:
  * Exploration early
  * Fine-tuning later


### 7. Elitism

* Best schedule is always preserved into the next generation


### 8. Termination Criteria

* Minimum **100 generations**
* Stops when:

  * Mutation rate has been reduced multiple times AND
  * Improvement remains below 1%

---

## Results & Observations

* **Final Best Fitness:** ~13–14
* **Convergence:** Around generation 50–70
* **Mutation Rate:** Reduced multiple times during plateau phases

### Behavior:

* Rapid improvement in early generations
* Gradual plateau as solutions converge
* Mutation rate reduction improves stability

---

## Fitness Convergence

![Fitness Plot](../results/fitness_plot.png)

---

## Schedule Evaluation

The final generated schedule shows:

### Strengths:

* Minimal room conflicts
* Most activities assigned to preferred facilitators
* Improved room utilization over time
* Good handling of SLA 101 / 191 constraints

### Weaknesses:

* Some facilitators (e.g., Banks, Lock) are used heavily
* Minor inefficiencies in room sizing remain
* Trade-offs exist due to competing constraints

---

## Challenges

### 1. Mutation Rate Tuning

* Too high → random behavior, no convergence
* Too low → premature convergence

**Solution:**
Adaptive mutation rate (halving when plateau detected)


### 2. Balancing Constraints

* Conflicts between:

  * Room size
  * Facilitator load
  * Scheduling rules

**Solution:**
Weighted fitness function to balance trade-offs


## Design Decisions

* **Softmax Selection** → prevents early dominance
* **Uniform Crossover** → increases diversity
* **Elitism** → preserves best solutions
* **Adaptive Mutation** → improves convergence

---

## Outputs

| File                  | Description              |
| --------------------- | ------------------------ |
| `best_schedule.txt`   | Final optimized schedule |
| `fitness_history.csv` | Fitness per generation   |
| `fitness_plot.png`    | Convergence graph        |
| `run_*.log`           | Detailed generation logs |


## GUI Features (Bonus)

Run with:

```bash
python main.py --gui
```

Includes:

* Live fitness graph
* Facilitator load bar chart
* Room utilization pie chart
* Constraint violation tracker
* Real-time schedule display
* Adjustable population & mutation rate


## Dependencies


* Python 3.8+
* numpy
* matplotlib
* tkinter (built-in)

