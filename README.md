# AEDATS — DA 技术服务看板

Ticket / Work Order 数据看板（数据来源 D365 CRM），由 GitHub Pages 发布。

**当前状态：已暂停。** 自动更新已于 2026-11-25 停用。页面显示的是最后一次拉取的静态快照，拉取时间见页面右上角。

- `index.html`：看板页面。数据写在文件开头的「数据块」常量里（`PULLED`、`stock`、`noAction`、`woStock` 等）。

仓库里已经删除的内容（都可以从 git 历史中找回）：

- `reports/`：每日快照归档（2026-09-15 至 2026-11-25）
- `preview/`：配色方案草稿
- `genesys/`、`genesys-pages.js`、`.github/workflows/`：Genesys Hotline 数据采集脚本和定时任务
- Trengo DA WA 模块：该平台已停用

以后需要恢复更新时，再按新需求重新编写对应的更新代码。
