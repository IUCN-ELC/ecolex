#!/usr/bin/env bash

source `dirname $0`/common.sh

_help() {
    echo -e "Build a docker image based on current repo dir and variables present in current environment and files in deploy.manifest"
    echo -e "Usage:"
    echo -e "\t-g branch:  if specified git branch/tag to clone before build; Default is empty which means that current directory it is used; Could also be an existing git tag"
    echo -e "\t-l:  local build; Build with files from current directory; Otherwise clone a fresh repo in /tmp; Default false"
    echo -e "\t-t tag:  tag to push in git AND to create docker image with; Default is env \$EDW_BUILD_VER"
    echo -e "\t-n:  no-push, Do not create git tag AND do not push image to docker.hub; Default is false"
    echo -e "\t-y:  confirmed; Do not ask for user confirmation from stdin; Default is false"
    echo -e "\t-q:  quiet mode; Do not output on stdout; Assume -y; Default is false"
    echo -e "\t-h:  help; Display this message"
}

projects_images() {
    # output vars
    arr_docker_images=()
    arr_full_docker_images=()

    cd docker
    for dir in $(find * -maxdepth 0 -type d -print); do
        if [ -n "$dir" ]; then
            arr_docker_images+=("$dir")
        fi
    done
    cd - >/dev/null

    for img in "${arr_docker_images[@]}"; do
        local full_img=${EDW_BUILD_DOCKERHUB}/${EDW_DEPLOY_PROJECT}_${img}:${tag}
        arr_full_docker_images+=($full_img)
    done
}

git_checkout=
tag=$EDW_BUILD_VER
no_push=false
quiet=false
confirmation=n

while getopts ":g:t:nyqh" opt; do
    case "$opt" in
        g)
            git_checkout=$OPTARG
            ;;
        t)
            tag=$OPTARG
            ;;
        n)
            no_push=true
            ;;
        q)
            quiet=true
            confirmation=y
            ;;
        y)
            confirmation=y
            ;;
        h)
            _help
            exit 0
            ;;
        ?)
            echo "Invalid option: -$OPTARG" >&2
            _help
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            _help
            exit 1
            ;;
    esac
done
shift $((OPTIND-1))

if [ -n "$git_checkout" ]; then

else
    echo X
fi

# compute docker image names
projects_images


if [ "$quiet" = "false" ]; then
    echo -e "${Yellow}=======================================================${White}\n"
    echo "Building in dir: `pwd`"
    echo "Building based on git branch/tag: $git_checkout"
    # Explicit check for false here, just to be safe
    if [ -n "$git_force_checkout" ]; then
        echo "${Red}We shall force the git checkout${White}"
    fi
    if [ "$no_push" == "false" ]; then
        echo "${Red}We shall create git tag and push to docker.hub ($tag)${White}"
    fi

    echo -e "\n${Yellow}Building with env:${White}"
    env |grep -e'^EDW_'
    # TODO get this out of build - this is used at deploy time
    echo -e "\n${Yellow}Using files manifested in deploy.manifest:"
    echo -e " (Make sure these files exist relative to current directory and contain proper configuration)${White}"
    cat deploy.manifest
#    echo -e "\n *** Computed arguments:\n"
#    echo -e "git_checkout=$git_checkout\n\
#git_force_checkout=$git_force_checkout\n\
#tag=$tag\n\
#no_push=$no_push\n\
#quiet=$quiet\n\
#confirmed=$confirmed\n\
#"
#    echo -e "\n *** Rest of arguments:\n"
#    echo "$@"
#    echo -e "\n *** Building for:\n"
#    echo "${arr_full_docker_images[@]}"
    echo -e "\n${Yellow}=======================================================${White}"
    echo
    if [ "$confirmation" = "n" ]; then
        echo "${Yellow}Are you sure you want to proceed? (y/n)${White}"
        read confirmation
    fi
fi

if [ "$confirmation" != "y" -a "$confirmation" != "Y" ]; then
    exit 0
fi

# Update our local copy of the repo
git fetch || exit 1
git checkout "$git_force_checkout" ${git_checkout} || exit 1
git pull origin ${git_checkout} || [ -n "$git_force_checkout" ] && exit 1

# Build docker images

echo " .. go on .."