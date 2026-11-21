package dev.amo.maincontrol;

/** Localized display metadata. Authorization remains independent of menu visibility. */
public record Menu(
    String key, String labelKo, String labelEn, String labelZh, boolean visible, int position) {}
