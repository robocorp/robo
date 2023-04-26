package process

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"sync"

	"github.com/robocorp/robo/cli/paths"
)

type Process struct {
	name           string
	args           []string
	cmd            *exec.Cmd
	StdoutListener func(string)
	StderrListener func(string)
	Env            map[string]string
}

type Output struct {
	Stdout string
	Stderr string
}

func New(name string, args ...string) *Process {
	return &Process{name, args, nil, nil, nil, nil}
}

func (proc *Process) String() string {
	return fmt.Sprintf("Process[name='%v',args=%v]", proc.name, proc.args)
}

func (proc *Process) Run() (output *Output, err error) {
	var env []string
	if proc.Env != nil {
		if pathvar, ok := proc.Env["PATH"]; ok {
			if f, err := paths.FindExecutable(proc.name, pathvar); err == nil {
				proc.name = f
			}
		}

		env = make([]string, 0)
		for k, v := range proc.Env {
			env = append(env, fmt.Sprintf("%v=%v", k, v))
		}
	} else {
		env = os.Environ()
	}

	proc.cmd = exec.Command(proc.name, proc.args...)
	proc.cmd.Env = env

	var stdout, stderr string
	var wg sync.WaitGroup

	stdoutPipe, err := proc.cmd.StdoutPipe()
	if err != nil {
		panic(err)
	}

	stderrPipe, err := proc.cmd.StderrPipe()
	if err != nil {
		panic(err)
	}

	wg.Add(1)
	go func() {
		scanner := bufio.NewScanner(stdoutPipe)
		for scanner.Scan() {
			line := scanner.Text()
			if proc.StdoutListener != nil {
				proc.StdoutListener(line)
			}
			stdout += line + "\n"
		}
		wg.Done()
	}()

	wg.Add(1)
	go func() {
		scanner := bufio.NewScanner(stderrPipe)
		for scanner.Scan() {
			line := scanner.Text()
			if proc.StderrListener != nil {
				proc.StderrListener(line)
			}
			stderr += line + "\n"
		}
		wg.Done()
	}()

	err = proc.cmd.Run()
	wg.Wait()

	return &Output{stdout, stderr}, err
}
