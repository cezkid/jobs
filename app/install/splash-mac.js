// Loading splash for the Mac: on screen from the double-click until the start page shows.
// osascript -l JavaScript splash-mac.js <root folder> [--dry]   (start-mac.sh runs it before update)
// Closes when .data/window-ready is as new as .data/splash-start, after CAP_S, or on a click in it.
// --dry: builds the window, never shows it, runs the same wait w/ a 1 s cap, prints what it built as JSON.
// Why outside VS Code + every rule below: app/docs/app-window.md, plan-ejf.13.
ObjC.import('Cocoa');

// app/window/brand.py tokens (test_splash.py holds them equal); never yellow: yellow = clickable
var COLOURS = {
  light: { background: '#ffffff', title: '#000000', text: '#000000', hint: '#3a3a3a' },  // paper, ink, ink, ink-2
  dark: { background: '#1c1c1e', title: '#f2f2f2', text: '#f2f2f2', hint: '#bdbdbd' },   // desk, text-dark, text-dark, text-dark-2
};
var TEXT = { title: 'CEZ Job Finder', text: 'Opening...', hint: 'The first start can take a minute.' };
var APPEARANCE = { light: 'NSAppearanceNameAqua', dark: 'NSAppearanceNameDarkAqua' };
var CAP_S = 45, DRY_CAP_S = 1, POLL_S = 0.1;
// bridge hands these back as strings ($.NSFloatingWindowLevel) or too big (NSEventMaskAny) => literals
var FLOATING_LEVEL = 3, ACCESSORY_POLICY = 1, BORDERLESS = 0, BACKING_BUFFERED = 2;
var LEFT_MOUSE_DOWN = 1, EVENT_MASK = 0xFFFFFFFF, SPINNER_STYLE = 1;
var WIDTH = 380, HEIGHT = 250, ICON = 72;

function colour(hex) {
  var n = parseInt(hex.slice(1), 16);
  return $.NSColor.colorWithSRGBRedGreenBlueAlpha(((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255, 1);
}

function hexOf(nsColour) {
  var c = nsColour.colorUsingColorSpace($.NSColorSpace.sRGBColorSpace);
  var part = function (v) { return ('0' + Math.round(v * 255).toString(16)).slice(-2); };
  return '#' + part(c.redComponent) + part(c.greenComponent) + part(c.blueComponent);
}

function readWord(path) {
  var s = $.NSString.stringWithContentsOfFileEncodingError(path, $.NSUTF8StringEncoding, null);
  return s.isNil() ? '' : ObjC.unwrap(s).trim().toLowerCase();
}

// .data/look light | dark wins (app/look.py); anything else = the computer's appearance
function pickLook(root) {
  var word = readWord(root + '/.data/look');
  if (word === 'light' || word === 'dark') return word;
  var style = $.NSUserDefaults.standardUserDefaults.stringForKey('AppleInterfaceStyle');
  return !style.isNil() && ObjC.unwrap(style) === 'Dark' ? 'dark' : 'light';
}

function mtime(path) {
  var attrs = $.NSFileManager.defaultManager.attributesOfItemAtPathError(path, null);
  if (attrs.isNil()) return null;
  var date = attrs.objectForKey('NSFileModificationDate');
  return date.isNil() ? null : date.timeIntervalSince1970;
}

function screenUnderMouse() {
  var at = $.NSEvent.mouseLocation, screens = $.NSScreen.screens;
  for (var i = 0; i < screens.count; i++) {
    var f = screens.objectAtIndex(i).frame;
    if (at.x >= f.origin.x && at.x < f.origin.x + f.size.width && at.y >= f.origin.y && at.y < f.origin.y + f.size.height) {
      return screens.objectAtIndex(i);
    }
  }
  return $.NSScreen.mainScreen;
}

// labelWithString draws in the system label colour (white on paper in dark mode) => colour set here;
// centred by its measured width: the alignment constant differs between Intel and Apple chips
function label(words, font, hex, top, into) {
  var field = $.NSTextField.labelWithString(words);
  field.font = font;
  field.textColor = colour(hex);
  field.sizeToFit;
  var size = field.frame.size;
  field.setFrameOrigin($.NSMakePoint(Math.round((WIDTH - size.width) / 2), HEIGHT - top - size.height));
  into.addSubview(field);
  return field;
}

function run(argv) {
  var dry = argv.indexOf('--dry') !== -1;
  var root = argv.filter(function (a) { return a.slice(0, 2) !== '--'; })[0] || '.';
  var started = Date.now() / 1000;
  // read now: update swaps app/ for a new one while the splash is up
  var iconData = $.NSData.dataWithContentsOfFile(root + '/app/install/icon.icns');
  var look = pickLook(root), colours = COLOURS[look];

  var app = $.NSApplication.sharedApplication;
  app.setActivationPolicy(ACCESSORY_POLICY);  // no Dock icon
  var screen = screenUnderMouse().visibleFrame;
  var frame = $.NSMakeRect(Math.round(screen.origin.x + (screen.size.width - WIDTH) / 2),
    Math.round(screen.origin.y + (screen.size.height - HEIGHT) / 2), WIDTH, HEIGHT);
  var win = $.NSWindow.alloc.initWithContentRectStyleMaskBackingDefer(frame, BORDERLESS, BACKING_BUFFERED, false);
  win.level = FLOATING_LEVEL;  // VS Code's window would cover a normal one => blank again
  win.appearance = $.NSAppearance.appearanceNamed(APPEARANCE[look]);
  win.backgroundColor = colour(colours.background);
  win.opaque = true;
  win.hasShadow = true;
  win.releasedWhenClosed = false;
  var view = win.contentView;

  var hasIcon = false;
  if (!iconData.isNil()) {
    var image = $.NSImage.alloc.initWithData(iconData);
    if (!image.isNil()) {
      var picture = $.NSImageView.alloc.initWithFrame($.NSMakeRect((WIDTH - ICON) / 2, HEIGHT - 34 - ICON, ICON, ICON));
      picture.image = image;
      view.addSubview(picture);
      hasIcon = true;
    }
  }
  var title = label(TEXT.title, $.NSFont.boldSystemFontOfSize(20), colours.title, 118, view);
  var spinner = $.NSProgressIndicator.alloc.initWithFrame($.NSMakeRect((WIDTH - 20) / 2, HEIGHT - 176, 20, 20));
  spinner.style = SPINNER_STYLE;
  spinner.indeterminate = true;
  spinner.startAnimation(null);
  view.addSubview(spinner);
  var text = label(TEXT.text, $.NSFont.systemFontOfSize(14), colours.text, 186, view);
  var hint = label(TEXT.hint, $.NSFont.systemFontOfSize(12), colours.hint, 212, view);

  app.finishLaunching;
  if (!dry) win.orderFrontRegardless;  // in front w/o taking the keyboard from the app in use

  // splash-start missing (run by hand) => our own start
  var since = mtime(root + '/.data/splash-start');
  if (since === null) since = started;
  var cap = dry ? DRY_CAP_S : CAP_S, closed = 'cap';
  while (Date.now() / 1000 - started < cap) {
    // >=: whole-second filesystems give a ready file written in the same second the same time
    var ready = mtime(root + '/.data/window-ready');
    if (ready !== null && ready >= since) { closed = 'ready'; break; }
    // runUntilDate never delivers clicks; events are read here and dropped, never sent on (no focus taken)
    var event = app.nextEventMatchingMaskUntilDateInModeDequeue(EVENT_MASK,
      $.NSDate.dateWithTimeIntervalSinceNow(POLL_S), $.NSDefaultRunLoopMode, true);
    if (!event.isNil() && Number(event.type) === LEFT_MOUSE_DOWN && Number(event.windowNumber) === Number(win.windowNumber)) {
      closed = 'click';
      break;
    }
  }
  var report = dry ? JSON.stringify({
    shown: Boolean(win.visible), level: Number(win.level), policy: Number(app.activationPolicy),
    look: look, appearance: ObjC.unwrap(win.appearance.name), icon: hasIcon,
    used: { background: hexOf(win.backgroundColor), title: hexOf(title.textColor), text: hexOf(text.textColor), hint: hexOf(hint.textColor) },
    colours: COLOURS, text: [ObjC.unwrap(title.stringValue), ObjC.unwrap(text.stringValue), ObjC.unwrap(hint.stringValue)],
    cap: CAP_S, closed: closed, waited: Math.round((Date.now() / 1000 - started) * 100) / 100,
  }) : '';
  win.close;
  return report;
}
