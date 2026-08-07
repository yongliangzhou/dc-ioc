type __VLS_Props = {
    title: string;
    value?: number | string;
    unit?: string;
    prefix?: string;
    subtitle?: string;
    dot?: string;
    trend?: number;
    barValue?: number;
    progress?: number;
    progressColor?: string;
    barColor?: string;
    target?: number;
    targetLabel?: string;
    detail?: string;
    size?: 'sm' | 'md' | 'lg';
    decimals?: number;
    status?: 'normal' | 'warning' | 'danger';
    clickable?: boolean;
    valueClass?: string;
};
declare const _default: import("vue").DefineComponent<__VLS_Props, {}, {}, {}, {}, import("vue").ComponentOptionsMixin, import("vue").ComponentOptionsMixin, {
    click: () => any;
}, string, import("vue").PublicProps, Readonly<__VLS_Props> & Readonly<{
    onClick?: (() => any) | undefined;
}>, {
    barColor: string;
    size: "sm" | "md" | "lg";
    decimals: number;
    clickable: boolean;
}, {}, {}, {}, string, import("vue").ComponentProvideOptions, false, {}, any>;
export default _default;
