# 双人减 · 无密码身份切换

**Status:** approved  
**Date:** 2026-10-08

## Problem

私有共享 H5，固定两人（🐉 / 🍃）。密码登录多余；需要快速选人与随时切换。

## Decision

- 入口页只选身份，无密码。
- `POST /api/auth/select { user_id }` 发 JWT（不校验密码）；保留 `/login` 供测试兼容。
- 顶栏常驻身份切换；「我的」也可切换；「退出」清会话回选人页。
- 切换后刷新当前视图数据（路由 remount / reload）。

## Non-goals

- 不引入共享口令 / 设备绑定。
- 不删除 config 里的 password 字段（仍用于 seed / 旧 login 测试）。
