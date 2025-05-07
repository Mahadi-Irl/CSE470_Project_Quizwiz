from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from app import db
from app.models.user import User
from app.forms.auth import UpdateProfileForm

user_bp = Blueprint('user', __name__)

@user_bp.route('/user/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user/profile.html', user=user)

@user_bp.route('/user/<username>/edit', methods=['GET', 'POST'])
@login_required
def edit_profile(username):
    if username != current_user.username:
        flash('You can only edit your own profile.', 'danger')
        return redirect(url_for('user.profile', username=username))
    
    form = UpdateProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.bio = form.bio.data
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('user.profile', username=current_user.username))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.bio.data = current_user.bio
    return render_template('user/edit_profile.html', title='Edit Profile', form=form) 