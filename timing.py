"""Session timing: cached pages never count towards measured OCR throughput."""
def duration(seconds):
    seconds=max(0,int(seconds))
    return f'{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}'

class Estimate:
    def __init__(self,start):
        self.start=start;self.samples=[];self.done=0;self.total=0
    def update(self,done,total,now):
        self.done=done;self.total=total
        if not self.samples or done>self.samples[-1][1]:self.samples.append((now,done))
        self.samples=self.samples[-11:]
    def label(self,now):
        elapsed=duration(now-self.start)
        if self.total and self.done>=self.total:return f'Прошло {elapsed} · Осталось 00:00:00'
        if len(self.samples)<2:return f'Прошло {elapsed} · Осталось: идёт оценка…'
        first,last=self.samples[0],self.samples[-1]
        rate=(last[0]-first[0])/(last[1]-first[1])
        remaining=max(0,rate*(self.total-self.done)-(now-last[0]))
        if remaining==0:return f'Прошло {elapsed} · Осталось: уточняется…'
        return f'Прошло {elapsed} · Осталось ≈ {duration(remaining)}'
