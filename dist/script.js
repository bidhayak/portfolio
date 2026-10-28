const focuses = {
  data: { number: '01 / 04', title: 'Finding direction in data.', description: 'Python, data analysis, and recommendation systems.' },
  nlp: { number: '02 / 04', title: 'Making sense of text.', description: 'Text preprocessing, TF-IDF, and explainable job matching.' },
  systems: { number: '03 / 04', title: 'Built on a practical foundation.', description: 'Campus networks, Linux, Windows Server, and virtualization.' },
  cloud: { number: '04 / 04', title: 'Tools that bring teams together.', description: 'Microsoft Azure and Google Workspace administration.' }
};

document.querySelectorAll('[data-focus]').forEach((button) => {
  button.addEventListener('click', () => {
    const focus = focuses[button.dataset.focus];
    document.querySelectorAll('[data-focus]').forEach((node) => {
      const selected = node === button;
      node.classList.toggle('is-selected', selected);
      node.setAttribute('aria-pressed', String(selected));
    });
    document.querySelector('#focus-number').textContent = focus.number;
    document.querySelector('#focus-title').textContent = focus.title;
    document.querySelector('#focus-description').textContent = focus.description;
  });
});

document.querySelector('a[href="#project-approach"]').addEventListener('click', () => {
  document.querySelector('#project-approach').open = true;
});
function revealProjectApproach() {
  if (window.location.hash === '#project-approach') document.querySelector('#project-approach').open = true;
}
revealProjectApproach();
window.addEventListener('hashchange', revealProjectApproach);

const menuToggle = document.querySelector('.menu-toggle');
const mobileNav = document.querySelector('#mobile-nav');
function closeMenu() {
  menuToggle.setAttribute('aria-expanded', 'false');
  menuToggle.setAttribute('aria-label', 'Open navigation');
  mobileNav.hidden = true;
}
menuToggle.addEventListener('click', () => {
  const expanded = menuToggle.getAttribute('aria-expanded') === 'true';
  menuToggle.setAttribute('aria-expanded', String(!expanded));
  menuToggle.setAttribute('aria-label', expanded ? 'Open navigation' : 'Close navigation');
  mobileNav.hidden = expanded;
});
mobileNav.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeMenu));
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !mobileNav.hidden) {
    closeMenu();
    menuToggle.focus();
  }
});
document.addEventListener('click', (event) => {
  if (!mobileNav.hidden && !event.target.closest('.site-header')) closeMenu();
});

document.querySelector('.copy-email').addEventListener('click', async () => {
  const status = document.querySelector('.copy-status');
  const label = document.querySelector('.copy-email span');
  try {
    await navigator.clipboard.writeText('bidhayak2baral@gmail.com');
    label.textContent = 'Email copied';
    status.textContent = 'Copied to your clipboard. Say hello when you’re ready.';
  } catch {
    label.textContent = 'Copy email';
    status.textContent = 'Select and copy the email address above, or click it to open your email app.';
  }
});

document.querySelector('#year').textContent = new Date().getFullYear();

const messageDialog = document.querySelector('#contact-dialog');
const messageForm = document.querySelector('#message-form');
const messageStatus = document.querySelector('.message-form-status');
let messageOpener = null;
document.querySelectorAll('[data-open-contact]').forEach((button) => {
  button.addEventListener('click', () => {
    closeMenu();
    messageOpener = button;
    messageDialog.showModal();
    document.body.classList.add('dialog-is-open');
  });
});
document.querySelector('.dialog-close').addEventListener('click', () => messageDialog.close());
messageDialog.addEventListener('click', (event) => {
  const bounds = messageDialog.getBoundingClientRect();
  if (event.target === messageDialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) messageDialog.close();
});
messageDialog.addEventListener('close', () => {
  document.body.classList.remove('dialog-is-open');
  messageOpener?.focus({ preventScroll: true });
});

messageForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!messageForm.reportValidity()) return;
  if (messageForm.elements._honey.value) return;
  const submit = messageForm.querySelector('button[type="submit"]');
  if (submit.disabled) return;
  const label = submit.querySelector('span');
  const data = new FormData(messageForm);
  data.set('_subject', `Portfolio message: ${data.get('topic')}`);
  data.set('_url', window.location.href);
  submit.disabled = true;
  label.textContent = 'Sending…';
  messageStatus.textContent = '';
  messageStatus.classList.remove('is-error');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(messageForm.action, { method: 'POST', headers: { Accept: 'application/json' }, body: data, signal: controller.signal });
    let result;
    try {
      result = await response.json();
    } catch {
      throw new Error('The message service couldn’t respond. Please try again, or use the direct email link below.');
    }
    if (!response.ok || (result.success !== true && result.success !== 'true')) {
      if (/activat|confirm/i.test(result.message || '')) throw new Error('This form is being connected. Please use the direct email link below for now.');
      throw new Error('Your message couldn’t be sent. Please try again, or use the direct email link below.');
    }
    if (/activat|confirm your email/i.test(result.message || '')) throw new Error('This form is being connected. Please use the direct email link below for now.');
    messageStatus.textContent = 'Message submitted. Thank you for reaching out!';
    messageForm.reset();
  } catch (error) {
    messageStatus.classList.add('is-error');
    messageStatus.textContent = error.name === 'AbortError' ? 'That took too long. Your message is still here — try again, or use the email link below.' : (error instanceof TypeError ? 'Unable to connect. Your message is still here — try again, or use the email link below.' : error.message);
  } finally {
    clearTimeout(timeout);
    submit.disabled = false;
    label.textContent = 'Send message';
  }
});
