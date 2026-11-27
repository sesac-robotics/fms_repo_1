package dev.amo.control.application;

import dev.amo.control.domain.ReviewPlayback;

/** Optional demo-only source read in the operations snapshot transaction. */
public interface ReviewPlaybackSource {
  /** Returns the current synthetic run, or null when there is no active review. */
  ReviewPlayback current();
}
