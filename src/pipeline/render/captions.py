def segment_captions(text: str, max_words: int = 5) -> list[str]:
    words=text.split()
    return [' '.join(words[i:i+max_words]) for i in range(0,len(words),max_words)]


def _ass_time(seconds: float) -> str:
    seconds=max(0.0, seconds)
    h=int(seconds//3600); seconds-=h*3600
    m=int(seconds//60); seconds-=m*60
    s=int(seconds); cs=int(round((seconds-s)*100))
    if cs==100: s+=1; cs=0
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'


def build_ass_subtitles(text: str, duration: float, max_words: int = 5) -> str:
    groups=segment_captions(text,max_words=max_words)
    total_words=max(sum(len(g.split()) for g in groups),1)
    header='''[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,DejaVu Sans,64,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,0,2,80,80,410,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'''
    lines=[]; cursor=0.0
    for group in groups:
        span=duration*(len(group.split())/total_words)
        start=cursor; end=min(duration,cursor+span); cursor=end
        safe=group.upper().replace('{','').replace('}','').replace('\\','')
        lines.append(f'Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{safe}')
    return header+'\n'.join(lines)+'\n'
