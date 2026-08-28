# Dispatch week timetable

## Goal

Make dispatch understandable as one linear workflow while preserving the existing backend commands and business rules.

## Workflow

1. Select a pending Delivery Order.
2. Place it into a free vehicle slot on a Monday-Sunday timetable.
3. Confirm the main driver, assistant, packaging, and dispatch.

The weekly view is the default planning surface. Each vehicle owns one row and each day cell shows its actual trip time blocks, maintenance state, conflicts, or availability. The day view remains available for detailed 06:00-22:00 inspection.

## Interaction

- Desktop users can drag a DO into a free vehicle/day cell or click the cell.
- Touch users select the DO and then tap a free cell.
- Selecting a free cell sets both the planning date and vehicle before opening the crew panel.
- Busy and conflict cells open the existing trip detail instead of replacing the assignment.
- The existing dispatch endpoint, resource validation, capacity checks, and idempotency remain unchanged.

## Responsive behavior

The weekly grid keeps a fixed vehicle column and seven stable day columns inside a horizontal scroll area. The crew form spans the full workbench width on desktop and stacks below the timetable on mobile.
