export type CommandFocusTarget =
  | 'weather'
  | 'assistant'
  | 'media'
  | 'calendar'
  | 'context';

export type AssistantIntent =
  | 'open_weather'
  | 'open_assistant'
  | 'open_media'
  | 'open_calendar'
  | 'calendar_today'
  | 'daily_context';

export interface AssistantUiAction {
  type: 'open_focus_view';
  target: CommandFocusTarget;
}

export interface AssistantCommandRoute {
  action: AssistantUiAction;
  intent: AssistantIntent;
  response: string;
}

const WEATHER_TERMS = [
  'weather',
  'forecast',
  'temperature',
  'outside',
  'rain',
  'raining',
];

const MEDIA_TERMS = [
  'music',
  'song',
  'songs',
  'playlist',
  'playback',
  'spotify',
];

const CALENDAR_TERMS = [
  'calendar',
  'schedule',
  'events',
  'event',
  'meeting',
  'meetings',
  'appointments',
];

const TODAY_TERMS = ['today', 'daily', 'day'];

const CONTEXT_PHRASES = [
  'daily briefing',
  'what is my day like',
  'what does my day look like',
  'what should i focus on',
  'what goals am i working on',
  'what do i have today',
  'show my context',
  'show context',
];

const ACTION_TERMS = [
  'open',
  'show',
  'switch to',
  'go to',
  'take me to',
  'bring up',
];

function normalizeCommand(input: string): string {
  return input
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function includesAnyTerm(command: string, terms: string[]): boolean {
  const paddedCommand = ` ${command} `;

  return terms.some((term) => paddedCommand.includes(` ${term} `));
}

function asksForView(command: string, targetTerms: string[]): boolean {
  return (
    includesAnyTerm(command, targetTerms) &&
    ACTION_TERMS.some((action) => command.includes(action))
  );
}

function createRoute(
  intent: AssistantIntent,
  target: CommandFocusTarget,
  response: string,
): AssistantCommandRoute {
  return {
    action: {
      target,
      type: 'open_focus_view',
    },
    intent,
    response,
  };
}

export function routeAssistantCommand(
  input: string,
): AssistantCommandRoute | null {
  const command = normalizeCommand(input);

  if (!command) {
    return null;
  }

  if (CONTEXT_PHRASES.some((phrase) => command.includes(phrase))) {
    return createRoute(
      'daily_context',
      'context',
      'Opening your daily context.',
    );
  }

  if (
    includesAnyTerm(command, WEATHER_TERMS) ||
    asksForView(command, ['weather'])
  ) {
    return createRoute('open_weather', 'weather', 'Opening the weather view.');
  }

  if (
    includesAnyTerm(command, MEDIA_TERMS) ||
    asksForView(command, ['media'])
  ) {
    return createRoute('open_media', 'media', 'Opening the media view.');
  }

  if (
    includesAnyTerm(command, CALENDAR_TERMS) &&
    includesAnyTerm(command, TODAY_TERMS)
  ) {
    return createRoute(
      'calendar_today',
      'calendar',
      "Checking today's calendar.",
    );
  }

  if (
    includesAnyTerm(command, CALENDAR_TERMS) ||
    asksForView(command, ['calendar', 'schedule'])
  ) {
    return createRoute(
      'open_calendar',
      'calendar',
      'Opening the calendar view.',
    );
  }

  if (asksForView(command, ['assistant', 'mirrage'])) {
    return createRoute(
      'open_assistant',
      'assistant',
      'Opening the assistant view.',
    );
  }

  return null;
}
