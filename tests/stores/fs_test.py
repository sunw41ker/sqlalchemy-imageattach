import functools
import os
import os.path
import re

from pytest import raises
from werkzeug.test import Client
from werkzeug.wrappers import Response

from sqlalchemy_imageattach.stores.fs import (FileSystemStore,
                                              HttpExposedFileSystemStore)
from ..conftest import sample_images_dir
from .conftest import TestingImage, utcnow



def test_fs_store(tmpdir):
    fs_store = FileSystemStore(tmpdir.strpath, 'http://mock/img/')
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    with open(image_path, 'rb') as image_file:
        expected_data = image_file.read()
        image_file.seek(0)
        fs_store.store(image, image_file)
    with fs_store.open(image) as actual:
        actual_data = actual.read()
    assert expected_data == actual_data
    expected_url = 'http://mock/img/testing/234/1/1234.405x640.jpe'
    actual_url = fs_store.locate(image)
    assert expected_url == re.sub(r'\?.*$', '', actual_url)
    fs_store.delete(image)
    with raises(IOError):
        fs_store.open(image)
    tmpdir.remove()


remove_query = functools.partial(re.compile(r'\?.*$').sub, '')


def test_http_fs_store(tmpdir):
    http_fs_store = HttpExposedFileSystemStore(tmpdir.strpath)
    image = TestingImage(thing_id=1234, width=405, height=640,
                         mimetype='image/jpeg', original=True,
                         created_at=utcnow())
    image_path = os.path.join(sample_images_dir, 'iu.jpg')
    with open(image_path, 'rb') as image_file:
        expected_data = image_file.read()
        image_file.seek(0)
        http_fs_store.store(image, image_file)
    with http_fs_store.open(image) as actual:
        actual_data = actual.read()
    assert expected_data == actual_data
    expected_url = 'http://localhost/x.images/testing/234/1/1234.405x640.jpe'
    def app(environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        yield http_fs_store.locate(image)
    app = http_fs_store.wsgi_middleware(app)
    client = Client(app, Response)
    actual_url = client.get('/').data
    assert expected_url == remove_query(actual_url)
    response = client.get('/x.images/testing/234/1/1234.405x640.jpe')
    assert response.status_code == 200
    assert response.data == expected_data
    assert response.mimetype == 'image/jpeg'
    http_fs_store.delete(image)
    with raises(IOError):
        http_fs_store.open(image)
    tmpdir.remove()