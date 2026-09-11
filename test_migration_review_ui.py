import pytest
from smart_state import SmartSettings
from test_premium_ui import actions


def test_native_review_is_read_only_and_does_not_export_credentials(actions):
    ui=actions;engine=ui.engine;config=ui.config
    original=config.file_path.read_bytes()
    mode=engine.is_enabled
    ui.dispatch({'action':'preview_migration','settings':SmartSettings(kind='personal').to_dict(),
                 'expected_revision':config.get('config_revision',0),'request_id':'review'})
    review=ui.snapshot()['migration_review']
    assert config.file_path.read_bytes()==original and engine.is_enabled==mode
    assert ui.migration_proposal is not None
    assert review['request_id']=='review' and not review['switch_available']
    assert review['start']<review['ready']<review['neutral']
    assert 'ipc_token' not in str(review) and 'source_digest' not in review


def test_browser_cannot_supply_migration_approval(actions):
    ui=actions;config=ui.config
    with pytest.raises(ValueError,match='Unexpected'):
        ui.dispatch({'action':'preview_migration','settings':SmartSettings(kind='personal').to_dict(),
                     'expected_revision':config.get('config_revision',0),'previewed':True})
    assert ui.migration_proposal is None


def test_stale_migration_review_request_does_not_replace_native_proposal(actions):
    ui=actions;config=ui.config
    with pytest.raises(ValueError,match='changed'):
        ui.dispatch({'action':'preview_migration','settings':SmartSettings(kind='personal').to_dict(),
                     'expected_revision':-1})
    assert ui.migration_proposal is None


def test_current_native_review_can_commit_without_browser_binary_path(actions,monkeypatch):
    ui=actions;config=ui.config;calls=[]
    ui.app.begin_smart_migration=lambda proposal,binary_path:calls.append((proposal,binary_path))
    monkeypatch.setattr('premium_ui.sys.executable',str(config.file_path))
    ui.dispatch({'action':'preview_migration','settings':SmartSettings(kind='personal').to_dict(),
                 'expected_revision':config.get('config_revision',0),'request_id':'review'})
    review=ui.snapshot()['migration_review']
    assert review['switch_available'] is True
    message=ui.dispatch({'action':'commit_migration','review_id':review['review_id'],
                         'expected_revision':review['config_revision'],'request_id':'switch'})
    assert len(calls)==1 and calls[0][0] is ui.migration_proposal
    assert calls[0][1]==config.file_path
    assert message.startswith('Switching')


def test_switch_rejects_stale_or_browser_manufactured_review(actions,monkeypatch):
    ui=actions;config=ui.config;calls=[]
    ui.app.begin_smart_migration=lambda *args:calls.append(args)
    monkeypatch.setattr('premium_ui.sys.executable',str(config.file_path))
    with pytest.raises(ValueError,match='Review'):
        ui.dispatch({'action':'commit_migration','review_id':'invented','expected_revision':0})
    ui.dispatch({'action':'preview_migration','settings':SmartSettings(kind='personal').to_dict(),
                 'expected_revision':config.get('config_revision',0)})
    review=ui.snapshot()['migration_review']
    config.transactional_update({'unrelated':'newer'})
    with pytest.raises(ValueError,match='changed'):
        ui.dispatch({'action':'commit_migration','review_id':review['review_id'],
                     'expected_revision':review['config_revision']})
    assert calls==[] and ui.migration_proposal is None
