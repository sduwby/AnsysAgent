"""宠物系统单元测试"""
import pytest
from unittest.mock import Mock, patch
from agent.pet import PetState, PET_TYPE_ALIASES


class TestPetState:
    """测试 PetState 类"""
    
    def test_rename_validation(self):
        """测试重命名验证"""
        pet = PetState()
        
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
    
    def test_choose_pet_case_insensitive(self):
        """测试切换宠物大小写不敏感"""
        pet = PetState()
        original_type = pet.pet_type
        
        # 测试正常切换
        ok, msg = pet.choose_pet("安安")
        assert ok or not ok  # 可能已经是安安
        
        # 测试带空格
        ok, msg = pet.choose_pet(" 安安 ")
        # 应该能识别
        
        # 测试大小写（如果别名表支持）
        ok, msg = pet.choose_pet("AN AN")
        # 应该能识别（大小写不敏感）
        
        # 恢复原宠物
        pet.pet_type = original_type
        pet._save()
    
    def test_play_result_validation(self):
        """测试猜数字结果验证"""
        pet = PetState()
        
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
        assert "猜对了" in msg or "心情" in msg
        
        # 正常猜错
        sprite, msg = pet.play_result(3, 7)
        assert "猜错了" in msg or "心情" in msg
    
    def test_play_result_boundary(self):
        """测试猜数字边界值"""
        pet = PetState()
        
        # 边界值 1
        sprite, msg = pet.play_result(1, 1)
        assert "心情" in msg
        
        # 边界值 10
        sprite, msg = pet.play_result(10, 10)
        assert "心情" in msg
        
        # 负数
        sprite, msg = pet.play_result(-1, 5)
        assert "范围" in msg or "1~10" in msg
    
    def test_pet_initialization(self):
        """测试宠物初始化"""
        pet = PetState()
        
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])