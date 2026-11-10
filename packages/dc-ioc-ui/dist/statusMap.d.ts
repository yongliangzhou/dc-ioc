/** @dc-ioc/ui — 状态语义映射（唯一实现，供 StatusBadge 与单测共用） */
export interface StatusDef {
    /** 完整的 CSS 类名，已含 dui- 前缀；调用方不得再拼前缀 */
    cls: string;
    text: string;
}
export declare const STATUS_MAP: Record<string, StatusDef>;
export declare const DEFAULT_STATUS_CLASS = "dui-o";
/** 返回完整类名（不再由调用方拼接 'dui-' 前缀，避免 dui-dui-g 双前缀） */
export declare function statusClassOf(status: string | null | undefined): string;
/** 返回默认中文文案；未知状态原样回显，空值回显 '-' */
export declare function statusLabelOf(status: string | null | undefined): string;
