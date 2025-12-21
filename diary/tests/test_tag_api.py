# diary/tests/test_tag_api.py
"""
태그 API 테스트
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from diary.models import Tag, Diary, DiaryTag


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, db):
    """각 테스트마다 새 사용자 생성"""
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    user = User.objects.create_user(
        username=f'testuser_{unique_id}',
        email=f'test_{unique_id}@example.com',
        password='testpass123'
    )
    api_client.force_authenticate(user=user)
    api_client.user = user
    return api_client


def get_response_data(response):
    """페이지네이션 응답과 일반 응답 모두 처리"""
    data = response.data
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    return data


@pytest.mark.django_db(transaction=True)
class TestTagAPI:
    """태그 API 테스트"""

    def test_create_tag(self, authenticated_client):
        """태그 생성 테스트"""
        response = authenticated_client.post('/api/tags/', {
            'name': '일상',
            'color': '#FF6B6B'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == '일상'
        assert response.data['color'] == '#FF6B6B'

    def test_create_duplicate_tag(self, authenticated_client):
        """중복 태그 생성 실패 테스트"""
        # 첫 번째 태그 생성
        response1 = authenticated_client.post('/api/tags/', {'name': '중복테스트'})
        assert response1.status_code == status.HTTP_201_CREATED
        
        # 동일한 이름으로 두 번째 태그 생성 시도
        response2 = authenticated_client.post('/api/tags/', {'name': '중복테스트'})
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_tags(self, authenticated_client):
        """태그 목록 조회 테스트"""
        # 이 테스트 전용 태그 생성
        Tag.objects.create(user=authenticated_client.user, name='리스트태그1')
        Tag.objects.create(user=authenticated_client.user, name='리스트태그2')
        
        response = authenticated_client.get('/api/tags/')
        data = get_response_data(response)
        
        assert response.status_code == status.HTTP_200_OK
        # 이 사용자의 태그만 반환되어야 함
        assert len(data) == 2

    def test_update_tag(self, authenticated_client):
        """태그 수정 테스트"""
        tag = Tag.objects.create(user=authenticated_client.user, name='원본')
        
        response = authenticated_client.patch(f'/api/tags/{tag.id}/', {
            'name': '수정됨',
            'color': '#4ECDC4'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == '수정됨'
        assert response.data['color'] == '#4ECDC4'

    def test_delete_tag(self, authenticated_client):
        """태그 삭제 테스트"""
        tag = Tag.objects.create(user=authenticated_client.user, name='삭제할태그')
        
        response = authenticated_client.delete(f'/api/tags/{tag.id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Tag.objects.filter(id=tag.id).exists()

    def test_tag_isolation_between_users(self, api_client, db):
        """다른 사용자 태그 접근 불가 테스트"""
        import uuid
        unique1 = uuid.uuid4().hex[:8]
        unique2 = uuid.uuid4().hex[:8]
        
        # User1 생성 및 태그 생성
        user1 = User.objects.create_user(f'user1_{unique1}', f'user1_{unique1}@test.com', 'pass123')
        tag = Tag.objects.create(user=user1, name=f'user1tag_{unique1}')
        
        # User2로 접근 시도
        user2 = User.objects.create_user(f'user2_{unique2}', f'user2_{unique2}@test.com', 'pass123')
        api_client.force_authenticate(user=user2)
        
        response = api_client.get('/api/tags/')
        data = get_response_data(response)
        assert len(data) == 0  # user2에게는 태그가 없음
        
        response = api_client.get(f'/api/tags/{tag.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db(transaction=True)
class TestTagDiaryRelation:
    """태그-일기 관계 테스트"""

    def test_diary_with_tags(self, authenticated_client):
        """일기에 태그 추가 테스트"""
        tag1 = Tag.objects.create(user=authenticated_client.user, name='일기태그1')
        tag2 = Tag.objects.create(user=authenticated_client.user, name='일기태그2')
        
        response = authenticated_client.post('/api/diaries/', {
            'title': '태그 테스트',
            'content': '태그가 있는 일기입니다.',
            'tag_ids': [tag1.id, tag2.id]
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data['tags']) == 2

    def test_popular_tags(self, authenticated_client):
        """인기 태그 조회 테스트"""
        tag1 = Tag.objects.create(user=authenticated_client.user, name='인기태그1')
        tag2 = Tag.objects.create(user=authenticated_client.user, name='인기태그2')
        
        # tag1에 3개, tag2에 1개 일기 연결
        for i in range(3):
            diary = Diary.objects.create(
                user=authenticated_client.user,
                title=f'인기일기{i}',
                content=f'내용{i}'
            )
            DiaryTag.objects.create(diary=diary, tag=tag1)
        
        diary = Diary.objects.create(
            user=authenticated_client.user,
            title='인기일기4',
            content='내용4'
        )
        DiaryTag.objects.create(diary=diary, tag=tag2)
        
        response = authenticated_client.get('/api/tags/popular/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['tags'][0]['name'] == '인기태그1'  # 가장 많이 사용된 태그
