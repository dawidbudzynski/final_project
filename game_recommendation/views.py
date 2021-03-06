from collections import Counter
from operator import itemgetter

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.views import View

from game.models import Game
from .forms import ChooseTagsForm

DEVELOPER_MATCH_SCORE = 14
GENRE_MATCH_SCORE = 14
TAG_MATCH_SCORE = 12


class RecommendGamesManuallyView(View):
    def get(self, request):
        return render(
            request,
            template_name='recommend_games_manually.html',
            context={'form': ChooseTagsForm().as_p()}
        )

    def post(self, request):
        all_games_qs = Game.objects.all()
        form = ChooseTagsForm(request.POST)
        if form.is_valid():
            user_genre = form.cleaned_data['genre']
            user_developer = form.cleaned_data['developer']
            user_tags = form.cleaned_data['tags']

            all_games_info = []

            for game in self._assign_matching_tags_to_game(user_tags, all_games_qs):
                game_object = game['game_object']
                game_info = {
                    'game': game_object,
                    'matched_tags': [],
                    'unmatched_tags': []
                }
                match_score = 0

                if game_object.developer == user_developer:
                    game_info['developer_match'] = True
                    match_score += DEVELOPER_MATCH_SCORE
                else:
                    game_info['developer_match'] = False

                if game_object.genre == user_genre:
                    game_info['genre_match'] = True
                    match_score += GENRE_MATCH_SCORE
                else:
                    game_info['genre_match'] = False

                for game_tag in game_object.tags.all():
                    if game_tag in game['matching_tags']:
                        match_score += TAG_MATCH_SCORE
                        game_info['matched_tags'].append(game_tag)
                    else:
                        game_info['unmatched_tags'].append(game_tag)

                game_info['match_score'] = match_score
                all_games_info.append(game_info)

            ctx = {
                'sorted_all_game_information': sorted(
                    all_games_info, key=itemgetter('match_score'), reverse=True
                ),
                'user_favorites': {
                    'favorite_tags_top_6': user_tags,
                    'favorite_genre': user_genre,
                    'favorite_developer': user_developer
                }
            }

            return render(
                request,
                template_name='recommend_games_manually_result.html',
                context=ctx
            )

        messages.add_message(request, messages.ERROR, _('Form invalid'))
        return HttpResponseRedirect(reverse('game_recommendation:recommend-manually'))

    @staticmethod
    def _assign_matching_tags_to_game(user_tags, all_games_qs):
        """Returns all game objects with game tags which match user's favorites"""
        games_and_matching_tags = []
        for game in all_games_qs:
            matching_tags = list(set(game.tags.all()).intersection(user_tags))
            games_and_matching_tags.append({
                'game_object': game,
                'matching_tags': matching_tags
            })
        return games_and_matching_tags


class RecommendByRatedGamesView(View):
    def get(self, request):
        return render(
            request,
            template_name='recommend_by_rated_games.html',
            context={'to_be_rated': Game.objects.filter(to_be_rated=True)}
        )

    def post(self, request):
        games_rated = Game.objects.filter(to_be_rated=True)
        liked_games = [game for game in games_rated if request.POST["game_{}".format(game.id)] == 'like']

        liked_tags = []
        liked_genres = []
        liked_developers = []
        for game in liked_games:
            liked_tags = list(game.tags.all())
            liked_genres.append(game.genre)
            liked_developers.append(game.developer)

        favorite_tags = self.find_best_of_category(liked_tags, 6)
        favorite_genre = self.find_best_of_category(liked_genres, 1)
        favorite_developer = self.find_best_of_category(liked_developers, 1)

        all_games_info = []
        games_not_rated = list(set(Game.objects.all()) - set(games_rated))
        for game_object in games_not_rated:
            game_info = {
                'game': game_object,
                'matched_tags': [],
                'unmatched_tags': []
            }
            match_score = 0

            game_tags = list(game_object.tags.all())
            matching_tags = list(set(game_tags).intersection(favorite_tags))
            match_score += TAG_MATCH_SCORE * len(matching_tags)
            game_info['matched_tags'] = matching_tags
            game_info['unmatched_tags'] = [tag for tag in game_tags if tag not in matching_tags]

            if game_object.genre in favorite_genre:
                game_info['genre_match'] = True
                match_score += GENRE_MATCH_SCORE
            else:
                game_info['genre_match'] = False

            if game_object.developer in favorite_developer:
                game_info['developer_match'] = True
                match_score += DEVELOPER_MATCH_SCORE
            else:
                game_info['developer_match'] = False

            game_info['match_score'] = match_score

            all_games_info.append(game_info)

        ctx = {
            'sorted_all_game_information': sorted(
                all_games_info, key=itemgetter('match_score'), reverse=True
            ),
            'user_favorites': {
                'favorite_tags_top_6': favorite_tags,
                'favorite_genre': favorite_genre,
                'favorite_developer': favorite_developer
            }
        }

        return render(
            request,
            template_name='recommend_by_rated_games_result.html',
            context=ctx
        )

    @staticmethod
    def find_best_of_category(category, number_of_items):
        result = []
        counted_items = Counter(category).items()
        for element in sorted(counted_items, key=lambda x: x[1], reverse=True)[:number_of_items]:
            result.append(element[0])
        return result
