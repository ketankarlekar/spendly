from werkzeug.security import check_password_hash

from database.db import get_db


def test_get_register_renders_form(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert b'<form' in response.data


def test_register_success_redirects_to_login(client):
    response = client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123',
    })
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_register_hashes_password(app, client):
    client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123',
    })
    with app.app_context():
        user = get_db().execute(
            'SELECT password_hash FROM users WHERE email = ?', ('test@example.com',)
        ).fetchone()
    assert user is not None
    assert user['password_hash'] != 'password123'
    assert check_password_hash(user['password_hash'], 'password123')


def test_register_duplicate_email_shows_error(client):
    data = {'name': 'Test User', 'email': 'dup@example.com', 'password': 'password123'}
    client.post('/register', data=data)
    response = client.post('/register', data=data)
    assert response.status_code == 200
    assert b'already exists' in response.data


def test_register_short_password_shows_error(client):
    response = client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'short',
    })
    assert response.status_code == 200
    assert b'8 characters' in response.data


def test_register_missing_field_shows_error(client):
    response = client.post('/register', data={
        'name': '',
        'email': 'test@example.com',
        'password': 'password123',
    })
    assert response.status_code == 200
    assert b'All fields are required' in response.data


def test_register_error_repopulates_fields(client):
    response = client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'short',
    })
    assert b'Test User' in response.data
    assert b'test@example.com' in response.data
