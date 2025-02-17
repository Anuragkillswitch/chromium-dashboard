# Copyright 2022 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import testing_config  # Must be imported before the module under test.

from datetime import datetime

from api import converters
from internals.core_models import FeatureEntry, MilestoneSet, Stage


class ConvertersTest(testing_config.CustomTestCase):

  def setUp(self):
    self.date = datetime.now()
    self.fe_1 = FeatureEntry(
        id=123, name='feature template', summary='sum',
        creator_email='creator@example.com',
        updater_email='updater@example.com', category=1,
        owner_emails=['feature_owner@example.com'], feature_type=0,
        editor_emails=['feature_editor@example.com', 'owner_1@example.com'],
        impl_status_chrome=5, blink_components=['Blink'],
        spec_link='https://example.com/spec',
        sample_links=['https://example.com/samples'], standard_maturity=1,
        ff_views=5, ff_views_link='https://example.com/ff_views',
        ff_views_notes='ff notes', safari_views=1,
        bug_url='https://example.com/bug',
        launch_bug_url='https://example.com/launch_bug',
        safari_views_link='https://example.com/safari_views',
        safari_views_notes='safari notes', web_dev_views=1,
        web_dev_views_link='https://example.com/web_dev',
        doc_links=['https://example.com/docs'], other_views_notes='other notes',
        devrel_emails=['devrel@example.com'], prefixed=False,
        intent_stage=1, tag_review_status=1, security_review_status=2,
        privacy_review_status=1, feature_notes='notes',
        updated=self.date, accurate_as_of=self.date, created=self.date)
    self.fe_1.put()

    # Write stages for the feature.
    stage_types = [110, 120, 130, 140, 150, 151, 160]
    for s_type in stage_types:
      s = Stage(feature_id=self.fe_1.key.integer_id(), stage_type=s_type,
          milestones=MilestoneSet(desktop_first=1,
              android_first=1, desktop_last=2),
          intent_thread_url=f'https://example.com/{s_type}')
      # Add stage-specific fields.
      if s_type == 150:
        s.experiment_goals = 'goals'
        s.experiment_risks = 'risks'
        s.announcement_url = 'https://example.com/announce'
      elif s_type == 151:
        s.experiment_extension_reason = 'reason'
      elif s_type == 160:
        s.finch_url = 'https://example.com/finch'
      s.put()
    self.maxDiff = None

  def tearDown(self) -> None:
    self.fe_1.key.delete()
    for s in Stage.query():
      s.key.delete()

  def test_feature_entry_to_json_basic__normal(self):
    """Converts feature entry to basic JSON dictionary."""
    result = converters.feature_entry_to_json_basic(self.fe_1)
    expected = {
      'id': 123,
      'name': 'feature template',
      'summary': 'sum',
      'unlisted': False,
      'blink_components': ['Blink'],
      'breaking_change': False,
      'resources': {
        'samples': ['https://example.com/samples'],
        'docs': ['https://example.com/docs'],
      },
      'standards': {
        'spec': 'https://example.com/spec',
        'maturity': {
          'text': 'Unknown standards status - check spec link for status',
          'short_text': 'Unknown status',
          'val': 1,
        },
      },
      'browsers': {
        'chrome': {
          'bug': 'https://example.com/bug',
          'blink_components': ['Blink'],
          'devrel':['devrel@example.com'],
          'owners':['feature_owner@example.com'],
          'origintrial': False,
          'intervention': False,
          'prefixed': False,
          'flag': False,
          'status': {
            'text':'Enabled by default',
            'val': 5
          }
        },
        'ff': {
          'view': {
          'text': 'No signal',
          'val': 5,
          'url': 'https://example.com/ff_views',
          'notes': 'ff notes',
          }
        },
        'safari': {
          'view': {
          'text': 'Shipped/Shipping',
          'val': 1,
          'url': 'https://example.com/safari_views',
          'notes': 'safari notes',
          }
        },
        'webdev': {
          'view': {
          'text': 'Strongly positive',
          'val': 1,
          'url': 'https://example.com/web_dev',
          'notes': None,
          }
        },
        'other': {
          'view': {
            'notes': 'other notes',
          }
        }
      }
    }
    self.assertEqual(result, expected)

  def test_feature_entry_to_json_basic__bad_view_field(self):
    """Function handles if any views fields have deprecated values."""
    # Deprecated views enum value.
    self.fe_1.ff_views = 4
    self.fe_1.safari_views = 4
    self.fe_1.put()
    result = converters.feature_entry_to_json_basic(self.fe_1)
    self.assertEqual(5, result['browsers']['safari']['view']['val'])
    self.assertEqual(5, result['browsers']['ff']['view']['val'])

  def test_feature_entry_to_json_verbose__normal(self):
    """Converts feature entry to complete JSON with stage data."""
    result = converters.feature_entry_to_json_verbose(self.fe_1)
    # Remove the stages and gates objects for a more apt comparison.
    result.pop('stages')
    result.pop('gates')

    expected = {
      'id': 123,
      'name': 'feature template',
      'summary': 'sum',
      'unlisted': False,
      'api_spec': False,
      'breaking_change': False,

      # Intent fields
      'intent_to_implement_url': 'https://example.com/120',
      'intent_to_experiment_url': 'https://example.com/150',
      'intent_to_extend_experiment_url': 'https://example.com/151',
      'intent_to_ship_url': 'https://example.com/160',

      # Milestone fields
      'dt_milestone_desktop_start': 1,
      'dt_milestone_android_start': 1,
      'ot_milestone_desktop_start': 1,
      'ot_milestone_android_start': 1,
      'ot_milestone_desktop_end': 2,

      # Stage-specific fields
      'experiment_goals': 'goals',
      'experiment_risks': 'risks',
      'experiment_extension_reason': 'reason',
      'announcement_url': 'https://example.com/announce',
      'finch_url': 'https://example.com/finch',

      'is_released': True,
      'category': 'Web Components',
      'category_int': 1,
      'feature_type': 'New feature incubation',
      'feature_type_int': 0,
      'intent_stage': 'Start prototyping',
      'intent_stage_int': 1,
      'star_count': 0,
      'bug_url': 'https://example.com/bug',
      'launch_bug_url': 'https://example.com/launch_bug',
      'deleted': False,
      'devrel_emails': ['devrel@example.com'],
      'doc_links': ['https://example.com/docs'],
      'prefixed': False,
      'requires_embedder_support': False,
      'spec_link': 'https://example.com/spec',
      'sample_links': ['https://example.com/samples'],
      'created': {
        'by': 'creator@example.com',
        'when': str(self.date)
      },
      'updated': {
        'by': 'updater@example.com',
        'when': str(self.date)
      },
      'accurate_as_of': str(self.date),
      'resources': {
        'samples': ['https://example.com/samples'],
        'docs': ['https://example.com/docs'],
      },
      'standards': {
        'spec': 'https://example.com/spec',
        'maturity': {
          'text': 'Unknown standards status - check spec link for status',
          'short_text': 'Unknown status',
          'val': 1,
        },
      },
      'tag_review_status': 'Pending',
      'tag_review_status_int': 1,
      'security_review_status': 'Issues open',
      'security_review_status_int': 2,
      'privacy_review_status': 'Pending',
      'privacy_review_status_int': 1,
      'editors': ['feature_editor@example.com', 'owner_1@example.com'],
      'creator': 'creator@example.com',
      'comments': 'notes',
      'browsers': {
        'chrome': {
          'bug': 'https://example.com/bug',
          'blink_components': ['Blink'],
          'devrel':['devrel@example.com'],
          'owners':['feature_owner@example.com'],
          'desktop': 1,
          'android': 1,
          'origintrial': False,
          'intervention': False,
          'prefixed': False,
          'flag': False,
          'status': {
            'milestone_str': 1,
            'text': 'Enabled by default',
            'val': 5
          }
        },
        'ff': {
          'view': {
          'text': 'No signal',
          'val': 5,
          'url': 'https://example.com/ff_views',
          'notes': 'ff notes',
          }
        },
        'safari': {
          'view': {
          'text': 'Shipped/Shipping',
          'val': 1,
          'url': 'https://example.com/safari_views',
          'notes': 'safari notes',
          }
        },
        'webdev': {
          'view': {
          'text': 'Strongly positive',
          'val': 1,
          'url': 'https://example.com/web_dev',
          }
        },
        'other': {
          'view': {
            'notes': 'other notes',
          }
        }
      }
    }
    self.assertEqual(result, expected)

  def test_feature_entry_to_json_verbose__bad_view_field(self):
    """Function handles if any views fields have deprecated values."""
    # Deprecated views enum value.
    self.fe_1.safari_views = 4
    self.fe_1.ff_views = 4
    self.fe_1.put()
    result = converters.feature_entry_to_json_verbose(self.fe_1)
    self.assertEqual(5, result['browsers']['safari']['view']['val'])
    self.assertEqual(5, result['browsers']['ff']['view']['val'])
