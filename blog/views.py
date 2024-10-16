from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count
from django.shortcuts import render, get_object_or_404
from taggit.models import Tag
from .models import *
from django.http import Http404, HttpResponse
from django.views.generic import ListView
from .forms import EmailPostForm, CommentForm
from django.core.mail import send_mail
from django.views.decorators.http import require_POST


# Function-based list_view
def post_list(request, tag_slug=None):
    post_list = Post.published.all()
    # include tagging
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])
    # Pagination with 3 posts per page
    paginator = Paginator(post_list, 2)
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except EmptyPage:
        # If page_number is out of range, get last page of results
        posts = paginator.page(paginator.num_pages)
    except PageNotAnInteger:
        # If page_number is not an integer get the first page
        posts = paginator.page(1)
    context = {
        'posts': posts,
        'tag': tag,
    }
    return render(request, 'blog/post/list.html', context)


# class PostListView(ListView):
#     """
#     Alternative post list view
#     """
#     # model = Post
#     queryset = Post.published.all()
#     context_object_name = 'posts'
#     paginate_by = 3
#     template_name = 'blog/post/list.html'


def post_detail(request, year, month, day, post):
    # try:
    #     post = Post.published.get(id=id)
    # except Post.DoesNotExist:
    #     raise Http404('No Post Found!')
    # post = get_object_or_404(Post, id=id, status=Post.Status.PUBLISHED)
    post = get_object_or_404(Post, status=Post.Status.PUBLISHED,
                             slug=post, publish__year=year,
                             publish__month=month, publish__day=day)

    # List of active comments for this post
    comments = post.comments.filter(active=True)

    # Form for users to comment
    form = CommentForm()

    # List of similar posts based on tags
    post_tags_ids = post.tags.values_list('id', flat=True)
    # the number of tags shared with all the tags queried
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    # Display recent posts first
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]

    context = {
        'post': post,
        'comments': comments,
        'form': form,
        'similar_posts': similar_posts,
    }
    return render(request, 'blog/post/detail.html', context)


def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    sent = False
    if request.method == 'POST':
        # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Form fields passed validation
            cd = form.cleaned_data
            #send email
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = (f'{cd['name']} ({cd['email']}) '
                       f'recommends you read {post.title}')
            message = f'Read {post.title} at {post_url}\n\n' \
                      f'{cd['name']}\'s comments: {cd['comments']}'
            send_mail(subject=subject, message=message, from_email=None, recipient_list=[cd['to']])
            sent = True
    else:
        form = EmailPostForm()

    context = {
        'post': post,
        'form': form,
        'sent': sent,
    }
    return render(request, 'blog/post/share.html', context)


@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    comment = None
    # A comment was posted
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # Create a Comment object without saving it to the database
        comment = form.save(commit=False)
        # Assign the post to the comment
        comment.post = post
        # Save the comment to the database
        comment.save()
    context = {
        'post': post,
        'form': form,
        'comment': comment,
    }
    return render(request, 'blog/post/comment.html', context)

