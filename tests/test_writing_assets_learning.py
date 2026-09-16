from pipeline.writing.tournament import normalize_hooks, choose_best_script
from pipeline.writing.models import ScriptCandidate
from pipeline.assets.pexels import choose_best_video
from pipeline.render.captions import segment_captions
from pipeline.learning.store import record_post_metrics
from pipeline.learning.weights import derive_category_weights


def test_normalize_hooks_sorts_by_score():
    payload={'hooks':[{'text':'weak','score':40},{'text':'strong','score':91}]}
    hooks=normalize_hooks(payload)
    assert hooks[0].text=='strong'


def test_choose_best_script_enforces_floor():
    scripts=[ScriptCandidate('a',70,'h'), ScriptCandidate('b',88,'h')]
    assert choose_best_script(scripts,80).text=='b'


def test_choose_best_video_prefers_portrait_and_non_recent():
    videos=[
      {'url':'old','width':1080,'height':1920,'quality':'hd'},
      {'url':'land','width':1920,'height':1080,'quality':'hd'},
      {'url':'portrait','width':1080,'height':1920,'quality':'hd'}]
    chosen=choose_best_video(videos, {'old'})
    assert chosen['url']=='portrait'


def test_caption_groups_are_readable():
    groups=segment_captions('one two three four five six seven eight', max_words=4)
    assert groups == ['one two three four','five six seven eight']


def test_learning_weights_reward_better_categories(tmp_path):
    db=str(tmp_path/'p.sqlite')
    record_post_metrics(db, {'post_id':'1','category':'technology','views':10000,'likes':1000,'comments':100,'shares':200})
    record_post_metrics(db, {'post_id':'2','category':'story','views':1000,'likes':20,'comments':1,'shares':2})
    weights=derive_category_weights(db)
    assert weights['technology'] > weights['story']
