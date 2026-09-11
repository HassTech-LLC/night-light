"""Opt-in local timing estimates. No application, keyboard or content logging."""
from datetime import datetime, timedelta
from statistics import median
from smart_migration import uses_v2


def clock_minutes(text):
    value = datetime.strptime(text, '%H:%M')
    return value.hour*60+value.minute


def estimate(nights):
    valid=[]
    for entry in nights[-14:]:
        try:
            sleep=float(entry['sleep']); wake=float(entry['wake'])
            if 0 <= sleep < 1440 and 0 <= wake < 1440:
                valid.append((sleep if sleep>=720 else sleep+1440,wake))
        except (ValueError,TypeError,KeyError):
            continue
    if len(valid)<7:
        return None, 'Low', len(valid)
    center=median(s for s,w in valid)
    valid=[(s,w) for s,w in valid if abs(s-center)<=180]
    if len(valid)<7:
        return None,'Low',len(valid)
    spread=median(abs(s-center) for s,w in valid)
    if spread>90:
        return None,'Low',len(valid)
    return (round(median(s for s,w in valid))%1440,round(median(w for s,w in valid))%1440), ('High' if len(valid)>=12 and spread<=30 else 'Medium'),len(valid)


class TimingLearner:
    def __init__(self,config):
        self.config=config
        self.last_active=None
        self.pending=None

    def reset(self):
        self.last_active=self.pending=None
        self.config.set('smart_nights',[])

    def record(self,sleep,wake):
        if uses_v2(self.config):
            self.last_active=self.pending=None
            return
        hours=(wake.timestamp()-sleep.timestamp())/3600
        if not 3<=hours<=14:
            return
        nights=self.config.get('smart_nights',[])
        if not isinstance(nights,list): nights=[]
        key=sleep.date().isoformat()
        entry={'date':key,'sleep':sleep.hour*60+sleep.minute,'wake':wake.hour*60+wake.minute}
        nights=[n for n in nights if isinstance(n,dict) and n.get('date')!=key]
        self.config.set('smart_nights',(nights+[entry])[-14:])

    def observe(self,now,idle_seconds):
        if uses_v2(self.config) or self.config.get('smart_learning',False) is not True:
            self.last_active=self.pending=None
            return
        if idle_seconds is None:
            return
        # Only a sustained >=30-minute idle boundary followed by >=3-minute
        # activity can become a candidate. Estimates are explicitly not sleep facts.
        if idle_seconds>=1800:
            self.last_active=now-timedelta(seconds=idle_seconds)
            self.pending=None
        elif idle_seconds<60 and self.last_active is not None:
            if self.pending is None:
                self.pending=now
            elif (now-self.pending).total_seconds()>=180:
                self.record(self.last_active,self.pending)
                self.last_active=self.pending=None
        else:
            self.pending=None
