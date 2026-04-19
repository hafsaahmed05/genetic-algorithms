from config import ACTIVITIES, ROOMS, TIMES, FACILITATORS

def calculate_fitness(schedule):
    fitness = 0.0
    
    # Trackers
    room_time_map = {}
    fac_load = {f: 0 for f in FACILITATORS}
    fac_time_map = {f: {t: [] for t in TIMES} for f in FACILITATORS}
    
    for act, details in schedule.items():
        room = details['room']
        time = int(details['time'])
        fac = str(details['fac'])
        
        # Room overlap tracking
        rt = (str(room), time)
        if rt not in room_time_map: room_time_map[rt] = []
        room_time_map[rt].append(act)
        
        # Facilitator tracking
        fac_load[fac] += 1
        fac_time_map[fac][time].append((act, room))
        
        # Room size constraints
        cap = ROOMS[room]
        enr = ACTIVITIES[act]['enrollment']
        if cap < enr:
            fitness -= 0.5
        elif cap > 3 * enr:
            fitness -= 0.4
        elif cap > 1.5 * enr:
            fitness -= 0.2
        else:
            fitness += 0.3
            
        # Facilitator assignments
        if fac in ACTIVITIES[act]['pref']:
            fitness += 0.5
        elif fac in ACTIVITIES[act]['other']:
            fitness += 0.2
        else:
            fitness -= 0.1
            
    # Resolve Room overlap conflicts
    for rt, acts in room_time_map.items():
        if len(acts) > 1:
            fitness -= (0.5 * len(acts))
            
    # Resolve Facilitator loads
    for f in FACILITATORS:
        load = fac_load[f]
        if load > 4:
            fitness -= 0.5
        elif load > 0 and load < 3: # 1 or 2 activities
            if f == 'Tyler' and load <= 1: # No penalty for Tyler if load == 1
                pass
            else:
                fitness -= 0.4
                
        # Time slot counts for facilitator
        times_scheduled = sorted([t for t in TIMES if len(fac_time_map[f][t]) > 0])
        for t in times_scheduled:
            acts_in_slot = len(fac_time_map[f][t])
            if acts_in_slot == 1:
                fitness += 0.2
            elif acts_in_slot > 1:
                fitness -= (0.2 * acts_in_slot)
                
        # Facilitator Consecutive time slots
        for i in range(len(times_scheduled) - 1):
            t1 = times_scheduled[i]
            t2 = times_scheduled[i+1]
            if t2 - t1 == 1:
                # Add 0.5 for consecutive
                fitness += 0.5
                # Romans/Beach logic
                for act1, r1 in fac_time_map[f][t1]:
                    for act2, r2 in fac_time_map[f][t2]:
                        hrb1 = ('Roman' in r1 or 'Beach' in r1)
                        hrb2 = ('Roman' in r2 or 'Beach' in r2)
                        if hrb1 != hrb2:
                            fitness -= 0.4

    # Activity specifics: SLA 101 A and B
    s101a = schedule.get('SLA101A')
    s101b = schedule.get('SLA101B')
    if s101a and s101b:
        diff = abs(int(s101a['time']) - int(s101b['time']))
        if diff > 4: fitness += 0.5
        elif diff == 0: fitness -= 0.5
        
    # Activity specifics: SLA 191 A and B
    s191a = schedule.get('SLA191A')
    s191b = schedule.get('SLA191B')
    if s191a and s191b:
        diff = abs(int(s191a['time']) - int(s191b['time']))
        if diff > 4: fitness += 0.5
        elif diff == 0: fitness -= 0.5
        
    # Activity specifics: 191 and 101 consecutive
    for a191 in ['SLA191A', 'SLA191B']:
        for a101 in ['SLA101A', 'SLA101B']:
            if a191 in schedule and a101 in schedule:
                t1 = int(schedule[a191]['time'])
                t2 = int(schedule[a101]['time'])
                r1 = str(schedule[a191]['room'])
                r2 = str(schedule[a101]['room'])
                diff = abs(t1 - t2)
                if diff == 1:
                    fitness += 0.5
                    hrb1 = ('Roman' in r1 or 'Beach' in r1)
                    hrb2 = ('Roman' in r2 or 'Beach' in r2)
                    if hrb1 != hrb2:
                        fitness -= 0.4
                elif diff == 2:
                    fitness += 0.25
                elif diff == 0:
                    fitness -= 0.25
                    
    return fitness