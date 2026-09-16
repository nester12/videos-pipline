from dataclasses import dataclass
from pathlib import Path
import json, os, re

from pipeline.config import load_config
from pipeline.cost_guard import require_env
from pipeline.trends.models import TrendCandidate
from pipeline.trends.scout import collect_trends
from pipeline.ranking.topics import rank_topics
from pipeline.writing.gemini import GeminiClient
from pipeline.writing.production import generate_winning_script
from pipeline.assets.scene_plan import build_scene_plan
from pipeline.assets.pexels import search_pexels_videos, choose_best_video, download_video
from pipeline.audio.voice import synthesize_kokoro, get_duration
from pipeline.render.captions import build_ass_subtitles
from pipeline.render.ffmpeg_render import render_short
from pipeline.qa import validate_video
from pipeline.publishing.package import build_caption, write_publish_package
from pipeline.learning.weights import derive_category_weights

@dataclass(frozen=True)
class ProductionResult:
    status: str
    reason: str = ''
    package_dir: str = ''


def select_topic(items, recent_topics, category_weights):
    ranked=rank_topics(items,recent_topics,category_weights)
    if not ranked: raise RuntimeError('No safe trend candidate passed ranking')
    return ranked[0]


def _load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8')) if Path(path).exists() else default
    except Exception:
        return default


def _save_json(path, value):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')


def _trend_objects(raw):
    return [TrendCandidate(**x) for x in raw if isinstance(x,dict) and x.get('title')]


def _slug(text):
    value=re.sub(r'[^a-z0-9]+','-',text.lower()).strip('-')
    return value[:50] or 'video'


def produce_one(config: dict | None = None) -> ProductionResult:
    config=config or load_config()
    prod=config.get('production',{})
    minimum=float(prod.get('minimum_script_score',82))
    min_s=float(prod.get('min_seconds',25)); max_s=float(prod.get('max_seconds',55))
    data_dir=Path('data'); data_dir.mkdir(exist_ok=True)

    raw=_load_json(data_dir/'trends.json',[])
    trends=_trend_objects(raw)
    if not trends:
        trends=collect_trends(config)
        _save_json(data_dir/'trends.json',[x.__dict__ for x in trends])
    recent=_load_json(data_dir/'recent_topics.json',[])
    weights=dict(config.get('category_weights',{}))
    learned=derive_category_weights(str(data_dir/'performance.sqlite'))
    for k,v in learned.items(): weights[k]=v
    topic=select_topic(trends,recent,weights)

    gemini=GeminiClient(require_env('GEMINI_API_KEY'), model=os.getenv('GEMINI_MODEL','gemini-3.6-flash'))
    winner,research,hooks=generate_winning_script(topic,gemini,minimum_score=minimum)
    beats=build_scene_plan(winner,target_beats=int(prod.get('target_scene_beats',7)))
    if len(beats)<3: return ProductionResult('skipped','scene plan too short')

    work=Path('work'); work.mkdir(exist_ok=True)
    pexels_key=require_env('PEXELS_API_KEY')
    recent_assets=set(_load_json(data_dir/'recent_assets.json',[]))
    chosen_urls=[]; scene_files=[]
    for i,beat in enumerate(beats[:int(prod.get('max_scene_beats',9))]):
        videos=search_pexels_videos(beat.search_query,pexels_key,per_page=8)
        asset=choose_best_video(videos,recent_assets|set(chosen_urls))
        scene_path=str(work/f'scene_{i:02d}.mp4')
        download_video(asset['url'],scene_path)
        chosen_urls.append(asset['url']); scene_files.append(scene_path)

    narration=str(work/'narration.wav')
    synthesize_kokoro(winner.text,narration,voice=str(prod.get('voice','am_michael')),speed=float(prod.get('voice_speed',1.0)))
    duration=get_duration(narration)
    if duration<min_s or duration>max_s:
        return ProductionResult('skipped',f'narration duration {duration:.1f}s outside {min_s}-{max_s}s')
    ass_path=work/'captions.ass'; ass_path.write_text(build_ass_subtitles(winner.text,duration,max_words=int(prod.get('caption_words',4))),encoding='utf-8')
    final=str(work/'final.mp4')
    render_short(scene_files,narration,final,duration,str(ass_path))
    errors=validate_video(final,min_s,max_s)
    if errors: return ProductionResult('failed','; '.join(errors))

    hashtags=[topic.category,'explained','trending','story']
    caption=build_caption(winner.hook,hashtags)
    package_dir=str(Path('output')/_slug(topic.title))
    metadata={'topic':topic.__dict__,'script_score':winner.score,'hook_scores':[h.__dict__ for h in hooks],'research':research,'duration_seconds':round(duration,2),'assets':chosen_urls,'ai_generated':True}
    write_publish_package(final,caption,metadata,package_dir)
    recent=(recent+[topic.title])[-20:]; _save_json(data_dir/'recent_topics.json',recent)
    _save_json(data_dir/'recent_assets.json',list((list(recent_assets)+chosen_urls)[-80:]))
    return ProductionResult('exported','',package_dir)


def main():
    result=produce_one()
    print(json.dumps(result.__dict__,indent=2))
    if result.status not in {'exported'}:
        raise SystemExit(2)

if __name__=='__main__': main()
