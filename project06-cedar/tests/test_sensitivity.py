from cedar.scoring import sensitivity,dominance,score_package


def example():
    reqs=[{'id':'R19','mode':'scored','category':'operations'},{'id':'R26','mode':'scored','category':'support'}]
    def package(id,ops,support,cost):
        aa=[{'requirement_id':r,'state':'supported','score_low':v,'score_high':v} for r,v in [('R19',ops),('R26',support)]]
        return dict(id=id,eligible=True,assessments=aa,cost={'known_total':cost,'upper_total':cost},score=score_package(reqs,aa,'balanced'))
    return reqs,[package('A',90,10,100),package('B',40,80,100),package('C',30,70,110)]


def test_independent_weight_crossover_and_dominance():
    r,p=example(); s=sensitivity(p,r)['cases']
    # .25*40+80 > .25*90+10; 4*90+10 > 4*40+80
    assert s[0]['guaranteed_leaders']==['B']
    assert s[-1]['guaranteed_leaders']==['A']
    assert dominance(p)==[{'dominant':'B','dominated':'C'}]


def test_open_bounds_and_missing_score_prevent_false_certainty():
    r,p=example();p[2]['cost']['upper_total']=None
    assert dominance(p)==[]
    p[0]['assessments'][0].update(state='unresolved',score_low=0,score_high=100)
    s=sensitivity(p,r)['cases'][-1]
    assert not s['guaranteed_leaders']
    assert set(s['possible_leaders'])=={'A','B'}
