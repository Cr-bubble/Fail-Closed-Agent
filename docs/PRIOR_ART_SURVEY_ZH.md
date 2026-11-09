# 先前/同期工作調查(2026-11-09)

> 方法:6 個方向平行搜尋(arXiv API + 網路,共約 380 組查詢、123 篇不重複候選),
> 重疊度高者開原文深讀(5 篇),其餘 69 篇批次核對存在性與摘要,另逐條核對參考文獻 22 筆。
> 原始資料:`paper_exp/prior_art/raw_result.json`、`verdicts.txt`。

## 一句話結論

**arXiv 上沒有人發表過同一篇論文**;但「LLM 只路由到 typed 確定性操作 + 等價檢查後才 commit」
這個架構,**同一比賽有多支隊伍獨立做出來,且已有公開成果**(其中一份 2026-06 就公開)。
C1 的架構本身不能再宣稱是新的;論文的新穎性要改放在:保證命題、drift 分離、C2 量測、C3 驗證。

## A. 同一比賽(ICCAD 2026 Problem A)— 威脅最高

| 來源 | 公開時間 | 機制 | 與我們的差異(深讀程式碼/報告確認) |
|---|---|---|---|
| Zhangjin Zhao(cada1078,佳作 661.4/674):"Verifiable LLM Agent Framework for EDA",個人網頁標 **DAC 審稿中** | 網頁最早 2026-11-06 | 81 個 schema-typed tools、persistent state、snapshot → Yosys/ABC SAT-miter CEC + 結構檢查 → commit/rollback | 他們的 LLM 是 planner,結果當 observation 回饋(多步);我們一請求一 intent。無命題、無 routing 研究、無 fault injection。**同期、未發表 → 不能引用,但審稿人可能看過** |
| Jia-Heng Han(cada1079)Zenodo 課程報告(10.5281/zenodo.20917600) | **2026-06-26**(先於我們) | 42 個 typed tools、register-cut SAT miter、commit/revert | 多輪 tool loop、LLM 自己寫答案;register-cut 只比 PO + D(不含 CK/RN/SN);**大設計與 depth 最佳化會跳過驗證**(非 fail-closed);無名稱 grounding;無 routing 評估 |
| JerryFlyTiger/netlist-agent(GitHub) | 2026-08-31 | 65 個 typed tools;README:「模型只決定句子代表哪個操作,不計算答案」 | 主路由是 regex,LLM 只當 fallback 且為多輪 ReAct、自寫回答;只有 ABC 重合成走 cec 把關,規則式編輯直接改網表、無 rollback;無量測 |
| zcgilbert(cada1043,NTHU)GitHub | 2026-09-21 | 63 個 tools、**對當前設計檢查名稱(entity_guard)**、snapshot–CEC–rollback 交易 | regex 路由為主(674 題中 669 題兩模型答案相同 → LLM 幾乎沒在決定);**等價不確定時會 commit**(退回模擬);README 記錄一個「等價但錯誤」的誤路由 = 我們 drift 的非正式觀察 |
| netpilot(Zenodo 匿名 artifact) | 2026-07-09 | dispatch + 等價 shield | 只有程式碼 |

**沒找到**:主辦方的 contest overview 論文(可能之後出現在 ICCAD proceedings)、同學的 "Beyond Equivalence" 任何公開版本。

## B. 比賽外、必須引用的先前工作

| 論文 | 為什麼要引 | 區隔 |
|---|---|---|
| **AutoEDA**(arXiv 2508.01012;ACM TODAES 2026) | EDA 中「LLM 輸出 typed JSON IR、不寫 Tcl、確定性執行」的先例 | 4 個粗粒度 flow tools、驗證器會「修補」而非拒絕、不檢查設計結果 |
| **Route Before Response**(2611.07534,2026-11) | 跨領域同機制,**連 "fail-closed routing" 用詞都一樣** | 客服軟體;無狀態變更、無等價證明 |
| **AgenticECO**(2608.03738) | 已用 "fail-closed verification boundary";apply-on-copy、commit/rollback | LLM 寫程式產生編輯;結構等價非形式 LEC;實體 3D-IC ECO |
| **LATCH**(2610.16625) | 支持我們的論點:固定 recipe 目錄 98.2% vs LLM 自建程序 17.9% | FPGA timing、模擬檢查 |
| **Self-Evolved ABC**(2604.15082,DAC'26) | LLM 改碼後跑 ABC cec,時序用 depth-1 BMC(類似 register cut) | 改的是工具原始碼,非 NL 請求 |
| ChipXplore(2407.12749) | NL 探索硬體設計的經典先例 | 唯讀、LLM 寫開放式查詢 |
| Almasre & Alrahis, VTS 2026 "Towards LLM-Based Reasoning for Gate-Level Netlist Tasks" | 「讓 LLM 直接推理網表」的對照組 | 正是我們標題反對的路線 |

**C2(routing 研究)的子結論都已有前例,要寫成「在新領域的量化」而非「發現」:**
- 文件/說明比示範重要:Hsieh et al. 2023(2308.00675);description 改寫影響選擇(2505.18135、2602.14878)
- 例句檢索做意圖分類:Milios 2023(2309.10954)、Intent Detection in the Age of LLMs(2410.01627)
- 近義工具混淆是主要錯誤:DiaFORGE(2507.03336)、Rabinovich & Anaby-Tavor(2504.00914)、MetaTool
- 反例要預先處理:2610.24487 中 fine-tuned encoder 勝過 LLM(5 路由/22 分支),要說明我們的標籤空間(~80 個近義操作)不同
- **我們最獨特的數據點**:完整 catalog 已在 prompt 時,例句檢索只再加約 1 點 — 沒找到前例

**一般性的 proposer/verifier/commit 模式已是常見做法**(Cordon 2606.17573、GoEX 2404.06921、2605.20173 等),
"fail-closed" 一詞 2026 年非常普遍;"drift" 與 intent-based networking 的 intent drift、IaC 的 configuration drift 撞詞
→ 建議改稱 **"conformance drift"** 並明確定義。

## C. 論文需要的調整

1. **不能宣稱新的**:「LLM 路由到 typed 操作 + 等價檢查 commit/rollback」本身。寫成 established pattern,
   並承認多支比賽隊伍收斂到類似設計(可引用公開的 artifact)。
2. **可以宣稱的區隔**(已對照他隊原始碼確認):
   - LLM 處理**每一個**請求、**恰好一個** intent、回覆由確定性程式產生(他隊多為 regex 優先 + 多輪 tool loop + LLM 自寫回答)
   - register-cut 含 **CK/RN/SN**(cada1079 只比 PO + D)
   - **不確定即回滾**(cada1043 不確定時 commit、cada1079 大設計跳過驗證)
     → ⚠️ **我們目前的程式碼在 `_commit` 也是「不確定即放行」,這個區隔要等 code 修正後才成立,修正變成 P0**
   - 有假設的命題(A1–A4 + Proposition 1)、conformance drift 的分離與傳播量化(13/24)
   - C2 routing 量測研究(沒有任何一隊或論文做過)、C3 fault injection
3. 新增引用約 10–12 篇(B 表 + C2 的 3–4 篇 + 比賽公開 artifact);參考文獻頁目前 22 筆,一頁放得下約 40 筆。

## D. 參考文獻核對(22 筆)

- 20 筆正確(多數可再補 DOI/頁碼)
- [2] RTLFixer:第一作者為 Yun-Da Tsai → 改 "Y.-D. Tsai"
- [21] 同學的論文:**任何公開管道都找不到** → 照 DAC 規定走未發表工作揭露程序
- 注意:OpenReview 上有一篇 "Beyond Equivalence: Task-Level Verification…"(NeurIPS'26,未能開啟驗證),
  標題和 [21] 幾乎撞名,引用時要確認不會混淆

## E. 雙盲風險(緊急)

- `github.com/Cr-bubble/Fail-Closed-Agent` **公開**,repo 名稱與論文題目相符,
  `paper/routing-study` 分支含論文原稿、實驗數據、共同作者協商文件;搜尋引擎已收錄。
- 母 repo `CAD-Contest-2026-ProblemA/Agent` 也是公開(含 `cada1125` 隊號),是否改私有需團隊決定。

## F. 這次搜尋的限制

- WebSearch 每回合 200 次的額度在後段用完,「guarded execution」方向**完全沒搜到 DAC/ICCAD/MLCAD 等非 arXiv 會議論文集**
- arXiv API 因平行查詢頻繁回 429,部分查詢未完成
- ynl.it.com 部落格無法連線,內容未驗證(不要引用)
- 建議 11/18 截稿前再補一次:非 arXiv 會議論文集 + arXiv 上新出現的比賽論文
