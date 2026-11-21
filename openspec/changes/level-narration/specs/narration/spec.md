## ADDED Requirements

### Requirement: Growing text
Each answer SHALL come with a text in which level n is every segment of level n or lower, in reading order, and a
level SHALL only insert segments, never rewrite, drop or reorder earlier ones.

#### Scenario: A later level
- **WHEN** the narrator writes level 2 after level 1
- **THEN** every segment of level 1 is still present, unchanged and in the same order

### Requirement: Grounded figures
Every number in the text SHALL appear, as rounded, in the result rows of its level.

#### Scenario: A made-up figure
- **WHEN** a draft states a figure that no result value rounds to
- **THEN** the narrator asks once more with the problem listed, and drops the text if it still fails

### Requirement: Inline panels
Every panel SHALL appear right after the segment that introduces it, and a panel no segment introduces SHALL still
appear, introduced by its title.

#### Scenario: A refusal
- **WHEN** the model declines to write a level
- **THEN** each new panel of that level appears after a segment made of its title

### Requirement: Continuous detail
The slider SHALL move continuously: between level n and n+1, the words that level n+1 adds appear in place in
proportion to the position, and each of its panels appears once its sentence is complete. Moving the slider SHALL
NOT call the server.

#### Scenario: Halfway between two levels
- **WHEN** the reader drags to 1.5
- **THEN** level 1's text is shown in full and about half of the words level 2 adds have appeared, in place
