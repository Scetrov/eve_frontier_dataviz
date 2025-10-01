from typing import Dict, List, Type

_strategy_registry: Dict[str, 'BaseShaderStrategy'] = {}


class BaseShaderStrategy:
    id: str = "base"
    label: str = "Base Strategy"
    order: int = 1000  # for UI sorting

    def build(self, context, objects_by_type: dict):  # pragma: no cover - to be overridden
        raise NotImplementedError


def register_strategy(strategy_cls: Type['BaseShaderStrategy']):
    inst = strategy_cls()
    _strategy_registry[inst.id] = inst
    return strategy_cls


def get_strategies() -> List['BaseShaderStrategy']:
    return sorted(_strategy_registry.values(), key=lambda s: (s.order, s.id))


def get_strategy(strategy_id: str) -> 'BaseShaderStrategy | None':
    return _strategy_registry.get(strategy_id)


def register():  # pragma: no cover - placeholder
    pass


def unregister():  # pragma: no cover - placeholder
    _strategy_registry.clear()
