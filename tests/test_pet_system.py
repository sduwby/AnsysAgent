"""宠物系统单元测试"""
import pytest
from unittest.mock import patch
from pathlib import Path
from agent.pet import PetState, PET_TYPE_ALIASES


class TestPetState:
    """测试 PetState 类"""

    @pytest.fixture(autouse=True)
    def mock_save_path(self, tmp_path):
        """每个测试方法自动 mock pet.json 保存路径，避免污染用户数据。"""
        fake_path = tmp_path / "pet.json"
        with patch("agent.pet._pet_save_path", return_value=fake_path):
            yield PetState()

    def test_rename_validation(self, mock_save_path):
        """测试重命名验证"""
        pet = mock_save_path

        # 空名字
        ok, msg = pet.rename("")
        assert not ok
        assert "不能为空" in msg

        # 超长名字
        ok, msg = pet.rename("x" * 17)
        assert not ok
        assert "太长" in msg

        # 合法名字
        ok, msg = pet.rename("测试")
        assert ok
        assert pet.name == "测试"

    def test_choose_pet_normal(self, mock_save_path):
        """测试切换宠物 - 正常别名"""
        pet = mock_save_path

        # 测试中文别名
        ok, _ = pet.choose_pet("氟氟")
        assert ok is True
        assert pet.pet_type == "fluent_fox"

        # 切换回来
        ok, _ = pet.choose_pet("安安")
        assert ok is True
        assert pet.pet_type == "maxwell_cat"

    def test_choose_pet_with_spaces(self, mock_save_path):
        """测试切换宠物 - 带空格能正确 trim"""
        pet = mock_save_path

        ok, _ = pet.choose_pet(" 氟氟 ")
        assert ok is True
        assert pet.pet_type == "fluent_fox"

    def test_choose_pet_same_type(self, mock_save_path):
        """测试切换宠物 - 当前已经是该类型"""
        pet = mock_save_path
        assert pet.pet_type == "maxwell_cat"

        ok, msg = pet.choose_pet("安安")
        assert ok is False
        assert pet.name in msg

    def test_choose_pet_invalid(self, mock_save_path):
        """测试切换宠物 - 无效别名"""
        pet = mock_save_path

        ok, msg = pet.choose_pet("不存在的宠物")
        assert ok is False
        assert "找不到" in msg

    def test_play_result_validation(self, mock_save_path):
        """测试猜数字结果验证"""
        pet = mock_save_path

        # 类型错误
        sprite, msg = pet.play_result("5", 5)  # type: ignore
        assert "参数错误" in msg or "游戏参数" in msg

        # 超出范围 - 太小
        sprite, msg = pet.play_result(0, 5)
        assert "范围" in msg or "1~10" in msg

        # 超出范围 - 太大
        sprite, msg = pet.play_result(11, 5)
        assert "范围" in msg or "1~10" in msg

        # 目标数字超出范围
        sprite, msg = pet.play_result(5, 0)
        assert "范围" in msg or "错误" in msg

        # 正常猜对
        sprite, msg = pet.play_result(5, 5)
        assert "猜对了" in msg

        # 正常猜错
        sprite, msg = pet.play_result(3, 7)
        assert "猜错了" in msg

    def test_play_result_boundary(self, mock_save_path):
        """测试猜数字边界值"""
        pet = mock_save_path

        # 边界值 1
        sprite, msg = pet.play_result(1, 1)
        assert "心情" in msg

        # 边界值 10
        sprite, msg = pet.play_result(10, 10)
        assert "心情" in msg

        # 负数
        sprite, msg = pet.play_result(-1, 5)
        assert "范围" in msg or "1~10" in msg

    def test_pet_initialization(self, mock_save_path):
        """测试宠物初始化"""
        pet = mock_save_path

        # 基本属性
        assert hasattr(pet, 'name')
        assert hasattr(pet, 'hunger')
        assert hasattr(pet, 'mood')
        assert hasattr(pet, 'stamina')
        assert hasattr(pet, 'pet_type')

        # 默认值范围
        assert 0 <= pet.hunger <= 100
        assert 0 <= pet.mood <= pet.mood_cap
        assert 0 <= pet.stamina <= 100


class TestPetTypeAliases:
    """测试宠物类型别名"""

    def test_aliases_exist(self):
        """测试别名表存在且非空"""
        assert PET_TYPE_ALIASES
        assert len(PET_TYPE_ALIASES) > 0

    def test_aliases_format(self):
        """测试别名格式"""
        for alias, pet_type in PET_TYPE_ALIASES.items():
            assert isinstance(alias, str)
            assert isinstance(pet_type, str)
            assert alias  # 非空
            assert pet_type  # 非空

    def test_all_pets_have_aliases(self):
        """测试每种宠物类型都有别名"""
        expected_types = {"maxwell_cat", "fluent_fox", "mapdl_dog"}
        actual_types = set(PET_TYPE_ALIASES.values())
        assert expected_types.issubset(actual_types)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
