from flask_assets import Environment, Bundle
from .. import app


bundles = {
    'home_css': Bundle(
        'css/bootstrap.css',
        'css/bootstrap-theme.css',
        'css/style.css',
        output='gen/home.css',
        filters='cssmin'
    ),
    'home_js': Bundle(
        'js/jquery-3.5.1.min.js',
        'js/bootstrap.min.js',
        'js/script.js',
        output='gen/home.js',
        filters='jsmin'
    )
}

assets = Environment(app)
assets.register(bundles)

