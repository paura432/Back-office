import { spawn } from 'node:child_process';

const children = new Set();
let stopping = false;

function shutdown(exitCode) {
  if (stopping) return;
  stopping = true;
  process.exitCode = exitCode;
  for (const child of children) {
    try {
      process.kill(-child.pid, 'SIGTERM');
    } catch (error) {
      if (error.code !== 'ESRCH') throw error;
    }
  }
  const deadline = setTimeout(() => {
    for (const child of children) {
      try {
        process.kill(-child.pid, 'SIGKILL');
      } catch (error) {
        if (error.code !== 'ESRCH') throw error;
      }
    }
  }, 8000);
  deadline.unref();
}

function launch(command, args, cwd, supervised = true) {
  const child = spawn(command, args, { cwd, stdio: 'inherit', detached: true });
  children.add(child);
  child.once('error', (error) => {
    console.error(error);
    children.delete(child);
    shutdown(1);
  });
  child.once('exit', (exitCode) => {
    children.delete(child);
    if (supervised && !stopping) shutdown(exitCode || 1);
  });
  return child;
}

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));

try {
  for (const frontend of ['website', 'backoffice']) {
    const installer = launch('npm', ['ci', '--no-audit', '--no-fund'], `/app/${frontend}`, false);
    await new Promise((resolve, reject) => {
      installer.once('error', reject);
      installer.once('exit', (exitCode) => {
        if (exitCode === 0 && !stopping) resolve();
        else reject(new Error(`${frontend}: dependency installation interrupted or failed`));
      });
    });
  }
  if (!stopping) {
    for (const [frontend, port] of [['website', '3000'], ['backoffice', '3001']]) {
      launch(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '0.0.0.0', '--port', port, '--strictPort'], `/app/${frontend}`);
    }
  }
} catch (error) {
  if (!stopping) console.error(error);
  shutdown(1);
}