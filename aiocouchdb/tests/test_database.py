# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Alexander Shorin
# All rights reserved.
#
# This software is licensed as described in the file LICENSE, which
# you should have received as part of this distribution.
#

import json
import types

import aiocouchdb.client
import aiocouchdb.feeds
import aiocouchdb.database
import aiocouchdb.server

from aiocouchdb.client import urljoin
from . import utils


class DatabaseTestCase(utils.TestCase):

    def setUp(self):
        super().setUp()
        self.url_db = urljoin(self.url, 'db')
        self.db = aiocouchdb.database.Database(self.url_db)

    def test_init_with_url(self):
        self.assertIsInstance(self.db.resource, aiocouchdb.client.Resource)

    def test_init_with_resource(self):
        res = aiocouchdb.client.Resource(self.url_db)
        db = aiocouchdb.database.Database(res)
        self.assertIsInstance(db.resource, aiocouchdb.client.Resource)
        self.assertEqual(self.url_db, db.resource.url)

    def test_init_with_name(self):
        res = aiocouchdb.client.Resource(self.url_db)
        db = aiocouchdb.database.Database(res, dbname='foo')
        self.assertEqual(db.name, 'foo')

    def test_init_with_name_from_server(self):
        server = aiocouchdb.server.Server()
        db = yield from server.db('foo')
        self.assertEqual(db.name, 'foo')

    def test_exists(self):
        result = yield from self.db.exists()
        self.assert_request_called_with('HEAD', 'db')
        self.assertTrue(result)

    def test_exists_forbidden(self):
        with self.response(status=403):
            result = yield from self.db.exists()
            self.assert_request_called_with('HEAD', 'db')
        self.assertFalse(result)

    def test_exists_not_found(self):
        with self.response(status=404):
            result = yield from self.db.exists()
            self.assert_request_called_with('HEAD', 'db')
        self.assertFalse(result)

    def test_info(self):
        with self.response(data=b'{}'):
            result = yield from self.db.info()
            self.assert_request_called_with('GET', 'db')
        self.assertIsInstance(result, dict)

    def test_create(self):
        with self.response(data=b'{"ok": true}'):
            result = yield from self.db.create()
            self.assert_request_called_with('PUT', 'db')
        self.assertTrue(result)

    def test_delete(self):
        with self.response(data=b'{"ok": true}'):
            result = yield from self.db.delete()
            self.assert_request_called_with('DELETE', 'db')
        self.assertTrue(result)

    def test_all_docs(self):
        result = yield from self.db.all_docs()
        self.assert_request_called_with('GET', 'db', '_all_docs')
        self.assertIsInstance(result, aiocouchdb.feeds.ViewFeed)

    def test_all_docs_params(self):
        all_params = {
            'attachments': False,       
            'conflicts': True,
            'descending': True,
            'endkey': 'foo',
            'endkey_docid': 'foo_id',
            'include_docs': True,
            'inclusive_end': False,
            'limit': 10,
            'skip': 20,
            'stale': 'ok',
            'startkey': 'bar',
            'startkey_docid': 'bar_id',
            'update_seq': True
        }

        for key, value in all_params.items():
            yield from self.db.all_docs(**{key: value})
            if key in ('endkey', 'startkey'):
                value = json.dumps(value)
            self.assert_request_called_with('GET', 'db', '_all_docs',
                                            params={key: value})

    def test_all_docs_key(self):
        yield from self.db.all_docs('foo')
        self.assert_request_called_with('GET', 'db', '_all_docs',
                                        params={'key': '"foo"'})

    def test_all_docs_keys(self):
        yield from self.db.all_docs('foo', 'bar', 'baz')
        self.assert_request_called_with('POST', 'db', '_all_docs',
                                        data={'keys': ('foo', 'bar', 'baz')})

    def test_bulk_docs(self):
        yield from self.db.bulk_docs([{'_id': 'foo'}, {'_id': 'bar'}])
        self.assert_request_called_with('POST', 'db', '_bulk_docs',
                                        data=Ellipsis)
        data = self.request.call_args[1]['data']
        self.assertIsInstance(data, types.GeneratorType)
        self.assertEqual(b'{"docs": [{"_id": "foo"},{"_id": "bar"}]}',
                         b''.join(data))

    def test_bulk_docs_all_or_nothing(self):
        yield from self.db.bulk_docs([{'_id': 'foo'}, {'_id': 'bar'}],
                                     all_or_nothing=True)
        self.assert_request_called_with('POST', 'db', '_bulk_docs',
                                        data=Ellipsis)
        data = self.request.call_args[1]['data']
        self.assertIsInstance(data, types.GeneratorType)
        self.assertEqual(b'{"all_or_nothing": true, "docs": '
                         b'[{"_id": "foo"},{"_id": "bar"}]}',
                         b''.join(data))

    def test_bulk_docs_new_edits(self):
        yield from self.db.bulk_docs([{'_id': 'foo'}], new_edits=False)
        self.assert_request_called_with('POST', 'db', '_bulk_docs',
                                        data=Ellipsis,
                                        params={'new_edits': False})

    def test_changes(self):
        result = yield from self.db.changes()
        self.assertIsInstance(result, aiocouchdb.feeds.ChangesFeed)
        self.assert_request_called_with('GET', 'db', '_changes')

    def test_changes_longpoll(self):
        result = yield from self.db.changes(feed='longpoll')
        self.assertIsInstance(result, aiocouchdb.feeds.LongPollChangesFeed)
        self.assert_request_called_with('GET', 'db', '_changes',
                                        params={'feed': 'longpoll'})

    def test_changes_continuous(self):
        result = yield from self.db.changes(feed='continuous')
        self.assertIsInstance(result, aiocouchdb.feeds.ContinuousChangesFeed)
        self.assert_request_called_with('GET', 'db', '_changes',
                                        params={'feed': 'continuous'})

    def test_changes_eventsource(self):
        result = yield from self.db.changes(feed='eventsource')
        self.assertIsInstance(result, aiocouchdb.feeds.EventSourceChangesFeed)
        self.assert_request_called_with('GET', 'db', '_changes',
                                        params={'feed': 'eventsource'})

    def test_changes_doc_ids(self):
        yield from self.db.changes('foo', 'bar')
        self.assert_request_called_with('POST', 'db', '_changes',
                                        data={'doc_ids': ('foo', 'bar')},
                                        params={'filter': '_doc_ids'})

    def test_changes_assert_filter_doc_ids(self):
        with self.assertRaises(AssertionError):
            yield from self.db.changes('foo', 'bar', filter='somefilter')

    def test_changes_params(self):
        all_params = {
            'att_encoding_info': False,
            'attachments': True,
            'conflicts': True,
            'descending': True,
            'feed': 'continuous',
            'filter': 'some/filter',
            'heartbeat': 1000,
            'include_docs': True,
            'limit': 20,
            'since': 'now',
            'style': 'all_docs',
            'timeout': 3000,
            'view': 'some/view'
        }

        for key, value in all_params.items():
            yield from self.db.changes(**{key: value})
            params = {key: value}
            if key == 'view':
                params['filter'] = '_view'
            self.assert_request_called_with('GET', 'db', '_changes',
                                            params=params)

    def test_compact(self):
        yield from self.db.compact()
        self.assert_request_called_with('POST', 'db', '_compact')

    def test_compact_ddoc(self):
        yield from self.db.compact('ddoc')
        self.assert_request_called_with('POST', 'db', '_compact', 'ddoc')

    def test_document(self):
        result = yield from self.db.doc('docid')
        self.assert_request_called_with('HEAD', 'db', 'docid')
        self.assertIsInstance(result, self.db.document_class)

    def test_document_custom_class(self):
        class CustomDocument(object):
            def __init__(self, thing, **kwargs):
                self.resource = thing
        db = aiocouchdb.database.Database(self.url_db,
                                          document_class=CustomDocument)

        result = yield from db.doc('docid')
        self.assert_request_called_with('HEAD', 'db', 'docid')
        self.assertIsInstance(result, CustomDocument)
        self.assertIsInstance(result.resource, aiocouchdb.client.Resource)

    def test_document_docid_gen_fun(self):
        def custom_id():
            return 'foo'

        result = yield from self.db.doc(idfun=custom_id)
        self.assert_request_called_with('HEAD', 'db', 'foo')
        self.assertIsInstance(result, self.db.document_class)

    def test_document_docid_gen_fun_default_uuid(self):
        result = yield from self.db.doc()
        call_args, _ = self.request.call_args
        docid = call_args[-1].rsplit('/', 1)[-1]
        self.assertRegex(docid, '[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}')
        self.assert_request_called_with('HEAD', 'db', docid)
        self.assertIsInstance(result, self.db.document_class)

    def test_design_document(self):
        result = yield from self.db.ddoc('ddoc')
        self.assert_request_called_with('HEAD', 'db', '_design', 'ddoc')
        self.assertIsInstance(result, self.db.design_document_class)

    def test_design_document_custom_class(self):
        class CustomDocument(object):
            def __init__(self, thing, **kwargs):
                self.resource = thing
        db = aiocouchdb.database.Database(self.url_db,
                                          design_document_class=CustomDocument)

        result = yield from db.ddoc('_design/ddoc')
        self.assert_request_called_with('HEAD', 'db', '_design', 'ddoc')
        self.assertIsInstance(result, CustomDocument)
        self.assertIsInstance(result.resource, aiocouchdb.client.Resource)

    def test_document_get_item(self):
        doc = self.db['docid']
        with self.assertRaises(AssertionError):
            self.assert_request_called_with('HEAD', 'db', 'docid')
        self.assertIsInstance(doc, self.db.document_class)

    def test_design_document_get_item(self):
        doc = self.db['_design/ddoc']
        with self.assertRaises(AssertionError):
            self.assert_request_called_with('HEAD', 'db', '_design', 'ddoc')
        self.assertIsInstance(doc, self.db.design_document_class)

    def test_ensure_full_commit(self):
        yield from self.db.ensure_full_commit()
        self.assert_request_called_with('POST', 'db', '_ensure_full_commit')

    def test_missing_revs(self):
        yield from self.db.missing_revs({'docid': ['rev1', 'rev2']})
        self.assert_request_called_with('POST', 'db', '_missing_revs',
                                        data={'docid': ['rev1', 'rev2']})

    def test_purge(self):
        yield from self.db.purge({'docid': ['rev1', 'rev2']})
        self.assert_request_called_with('POST', 'db', '_purge',
                                        data={'docid': ['rev1', 'rev2']})

    def test_revs_diff(self):
        yield from self.db.revs_diff({'docid': ['rev1', 'rev2']})
        self.assert_request_called_with('POST', 'db', '_revs_diff',
                                        data={'docid': ['rev1', 'rev2']})

    def test_revs_limit(self):
        yield from self.db.revs_limit()
        self.assert_request_called_with('GET', 'db', '_revs_limit')

    def test_revs_limit_update(self):
        yield from self.db.revs_limit(42)
        self.assert_request_called_with('PUT', 'db', '_revs_limit', data=42)

    def test_security_get(self):
        with self.response(data=b'{"admins": {}, "members": {}}'):
            result = yield from self.db.security.get()
            self.assert_request_called_with('GET', 'db', '_security')
        self.assertEqual({'admins': {}, 'members': {}}, result)

    def test_security_get_empty(self):
        data = {
            'admins': {
                'users': [],
                'roles': []
            },
            'members': {
                'users': [],
                'roles': []
            }
        }

        result = yield from self.db.security.get()
        self.assert_request_called_with('GET', 'db', '_security')
        self.assertEqual(data, result)

    def test_security_update(self):
        data = {
            'admins': {
                'users': ['foo'],
                'roles': []
            },
            'members': {
                'users': [],
                'roles': ['bar', 'baz']
            }
        }

        yield from self.db.security.update(admins={'users': ['foo']},
                                           members={'roles': ['bar', 'baz']})
        self.assert_request_called_with('PUT', 'db', '_security', data=data)

    def test_security_update_merge(self):
        with self.response(data=b'''{
            "admins": {
                "users": ["foo"],
                "roles": []
            },
            "members": {
                "users": [],
                "roles": ["bar", "baz"]
            }
        }'''):
            yield from self.db.security.update(admins={'roles': ['zoo']},
                                               members={'users': ['boo']},
                                               merge=True)
            data = {
                'admins': {
                    'users': ['foo'],
                    'roles': ['zoo']
                },
                'members': {
                    'users': ['boo'],
                    'roles': ['bar', 'baz']
                }
            }
            self.assert_request_called_with('PUT', 'db', '_security', data=data)

    def test_security_update_merge_duplicate(self):
        with self.response(data=b'''{
            "admins": {
                "users": ["foo"],
                "roles": []
            },
            "members": {
                "users": [],
                "roles": ["bar", "baz"]
            }
        }'''):
            yield from self.db.security.update(admins={'users': ['foo', 'bar']},
                                               merge=True)
            data = {
                'admins': {
                    'users': ['foo', 'bar'],
                    'roles': []
                },
                'members': {
                    'users': [],
                    'roles': ['bar', 'baz']
                }
            }
            self.assert_request_called_with('PUT', 'db', '_security', data=data)

    def test_security_update_empty_admins(self):
        with self.response(data=b'{}'):
            yield from self.db.security.update_admins()
            data = {
                'admins': {
                    'users': [],
                    'roles': []
                },
                'members': {
                    'users': [],
                    'roles': []
                }
            }
            self.assert_request_called_with('PUT', 'db', '_security', data=data)

    def test_security_update_some_admins(self):
        with self.response(data=b'{}'):
            yield from self.db.security.update_admins(users=['foo'],
                                                      roles=['bar', 'baz'])
            data = {
                'admins': {
                    'users': ['foo'],
                    'roles': ['bar', 'baz']
                },
                'members': {
                    'users': [],
                    'roles': []
                }
            }
            self.assert_request_called_with('PUT', 'db', '_security', data=data)

    def test_security_update_empty_members(self):
        with self.response(data=b'{}'):
            yield from self.db.security.update_members()
            data = {
                'admins': {
                    'users': [],
                    'roles': []
                },
                'members': {
                    'users': [],
                    'roles': []
                }
            }
            self.assert_request_called_with('PUT', 'db', '_security', data=data)

    def test_security_update_some_members(self):
        with self.response(data=b'{}'):
            yield from self.db.security.update_members(users=['foo'],
                                                       roles=['bar', 'baz'])
            data = {
                'admins': {
                    'users': [],
                    'roles': []
                },
                'members': {
                    'users': ['foo'],
                    'roles': ['bar', 'baz']
                }
            }
            self.assert_request_called_with('PUT', 'db', '_security', data=data)

    def test_temp_view(self):
        result = yield from self.db.temp_view('fun(_)-> ok end')
        self.assert_request_called_with('POST', 'db', '_temp_view',
                                        data={'map': 'fun(_)-> ok end'})
        self.assertIsInstance(result, aiocouchdb.feeds.ViewFeed)

    def test_temp_view_reduce(self):
        result = yield from self.db.temp_view('fun(_)-> ok end', '_count')
        self.assert_request_called_with('POST', 'db', '_temp_view',
                                        data={'map': 'fun(_)-> ok end',
                                              'reduce': '_count'})
        self.assertIsInstance(result, aiocouchdb.feeds.ViewFeed)

    def test_temp_view_language(self):
        result = yield from self.db.temp_view('fun(_)-> ok end',
                                              language='erlang')
        self.assert_request_called_with('POST', 'db', '_temp_view',
                                        data={'map': 'fun(_)-> ok end',
                                              'language': 'erlang'})
        self.assertIsInstance(result, aiocouchdb.feeds.ViewFeed)

    def test_temp_view_params(self):
        all_params = {
            'att_encoding_info': False,
            'attachments': False,
            'conflicts': True,
            'descending': True,
            'endkey': 'foo',
            'endkey_docid': 'foo_id',
            'group': False,
            'group_level': 10,
            'include_docs': True,
            'inclusive_end': False,
            'keys': ['foo', 'bar'],
            'limit': 10,
            'reduce': True,
            'skip': 20,
            'stale': 'ok',
            'startkey': 'bar',
            'startkey_docid': 'bar_id',
            'update_seq': True
        }

        for key, value in all_params.items():
            yield from self.db.temp_view('fun(_)-> ok end', **{key: value})
            if key in ('endkey', 'startkey'):
                value = json.dumps(value)
            if key == 'keys':
                self.assert_request_called_with('POST', 'db', '_temp_view',
                                                data={'map': 'fun(_)-> ok end',
                                                      key: value})
            else:
                self.assert_request_called_with('POST', 'db', '_temp_view',
                                                data={'map': 'fun(_)-> ok end'},
                                                params={key: value})

    def test_view_cleanup(self):
        yield from self.db.view_cleanup()
        self.assert_request_called_with('POST', 'db', '_view_cleanup')
