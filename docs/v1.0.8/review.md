# v1.0.8 审查记录

## 关键决策

| 决策                                   | 理由                                         |
| -------------------------------------- | -------------------------------------------- |
| `tag_emotion` 从 Amygdala 移到 Ears    | 情绪标注是输入理解，不是安全检测             |
| Eyes/Whiskers/Ears → AMYGDALA 应激反射 | 哺乳动物神经学：感官→杏仁核有直连通路        |
| GrowthProtocol 拆为 4 个具名协议       | 无签名的 Protocol = Any，框架无法验证        |
| cerebrum → growth 成为禁止边           | 推理不直接产生副作用，与 PAWS/MOUTH 同类约束 |
| Thalamus.locate 不暴露 chroma/weights  | 框架协议不应暴露应用层搜索后端细节           |

## 遇到的问题

1. **Golden 测试更新**: `test_v510_builtin_equivalence.py` 和 `test_v510_organ_spec.py` 中的硬编码断言需要同步更新。共 3 个测试、6 个断言点。

2. **meowagent 测试预存问题**: `test_v04_colony.py` 等旧测试引用已移除的模块（`meowagent.colony.manager`、`KittenBase`），与 v1.0.8 无关。计划中 meowagent 在 v1.0.9 后单独适配。

3. **Paws 旧方法 delegate**: v1.0.7 添加了 `execute` 但 `touch_file`/`run_command`/`interact_with_tool` 未委托。v1.0.8 改为委托到 `execute`，统一入口。

## 验证结果

```
610 passed, 1 warning in 0.70s
```

- meowcat 独立测试：610/610 passed
- 新 Protocol isinstance 校验：全部通过
- wiring 边集合：53 条（+6）
- forbidden 边：4 条（+2）
