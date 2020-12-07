from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page
from django.views.generic import CreateView, View

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User


@cache_page(20, key_prefix='index_page')
def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'index.html', {
        'page': page,
        'paginator': paginator
        }
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.group_posts.all()[:12]
    paginator = Paginator(posts, 2)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request, "group.html", {
            "group": group,
            'page': page,
            'paginator': paginator
        }
    )


@login_required
def new_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, files=request.FILES or None)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('index')
        return render(
            request, 'new_post.html', {
                'form': form,
                'is_created': True,
            }
        )
    form = PostForm()
    return render(request, 'new_post.html', {
        'form': form,
        'is_created': True,
        }
    )


def profile(request, username):
    user_profile = get_object_or_404(User, username=username)
    posts = user_profile.posts.all()
    paginator = Paginator(posts, 5)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    following = False
    if request.user.is_authenticated and request.user != user_profile and Follow.objects.filter(
            user=request.user, author=user_profile).count() != 0:
        following = True
    else:
        following = False
    return render(request, 'profile.html', {
        'page': page,
        'paginator': paginator,
        'user_profile': user_profile,
        "following": following
        }
    )


def post_view(request, username, post_id):
    post_profile = get_object_or_404(Post, author__username=username,
                                     id=post_id)
    items = post_profile.comments.all()
    form = CommentForm()
    return render(request, 'post.html', {
        'post_profile': post_profile,
        'user_profile': post_profile.author,
        'items': items,
        'form': form
        }
    )


@login_required
def post_edit(request, username, post_id):
    post_profile = get_object_or_404(Post, author__username=username,
                                     id=post_id)
    form = PostForm(instance=post_profile)
    if post_profile.author == request.user:
        form_edited = PostForm(
            request.POST or None,
            files=request.FILES or None,
            instance=post_profile
        )
        if form_edited.is_valid():
            form_edited.save()
            return redirect('post', username=post_profile.author,
                            post_id=post_profile.id)
        return render(request, 'new_post.html', {
            'form': form,
            'post_profile': post_profile,
            }
        )
    return redirect('index')


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, id=post_id)
    items = post.comments.all()
    form = CommentForm(request.POST or None)
    if form.is_valid():
        new_comment = form.save(commit=False)
        new_comment.post = post
        new_comment.author = request.user
        new_comment.save()
        # return redirect('index')
    return redirect('post', username=post.author.username,
                        post_id=post.id)
    # return render(request, 'includes/comments.html', {
    #               'form': form,
    #               'items': items,
    #               'post_profile': post,
    #               'user_profile': post.author})


@login_required
def follow_index(request):
    post_list = Post.objects.filter(
        author__following__in=Follow.objects.filter(user=request.user))
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'follow.html', {
        'page': page,
        'paginator': paginator
        }
    )


@login_required
def profile_follow(request, username):
    user = get_object_or_404(User, username=username)
    if request.user != user and Follow.objects.filter(
            user=User.objects.get(username=request.user.username),
            author=User.objects.get(username=user.username)).count() == 0:
        Follow.objects.get_or_create(user=request.user, author=user)
        return redirect('profile', username=user.username)
    return redirect('profile', username=user.username)


@login_required
def profile_unfollow(request, username):
    user = get_object_or_404(User, username=username)
    if Follow.objects.filter(
            user=User.objects.get(username=request.user.username),
            author=User.objects.get(username=user.username)).count() != 0:
        Follow.objects.get(user=request.user, author=user).delete()
        return redirect('profile', username=user.username)
    return redirect('profile', username=user.username)


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)
