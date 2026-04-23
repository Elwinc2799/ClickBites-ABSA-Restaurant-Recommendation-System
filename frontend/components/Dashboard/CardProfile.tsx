import React, { ReactEventHandler } from 'react';
import Image from 'next/image';
import { useState } from 'react';
import Link from 'next/link';
import UpdateBusinessModal from './UpdateBusinessModal';

interface Business {
    _id: string;
    name: string;
    address: string;
    city: string;
    state: string;
    latitude: number;
    longitude: number;
    categories: string;
    description: string;
    business_pic: string;
}

interface CardProfileProps {
    business: Business | null;
}

function CardProfile({ business}: CardProfileProps) {
    const [showMore, setShowMore] = useState(false);

    const handleShowMoreClick = (
        event: React.MouseEvent<HTMLAnchorElement, MouseEvent>
    ) => {
        event.preventDefault();
        setShowMore(!showMore);
    };

    const description = business?.description ?? '';
    const shortDescription = description.length > 250 ? `${description.substring(0, 250)}...` : description;
    const fullDescription = description;

    return (
        <>
            <div className="flex flex-col min-w-0 break-words bg-white w-4/12 h-auto min-h-[840px] mb-6 shadow-xl rounded-lg mt-20">
                <div className="flex flex-wrap justify-center">
                    <div className="w-full flex justify-center">
                        <div className="w-full">
                            <Image
                                alt="..."
                                src={
                                    business?.business_pic
                                        ? `/business_photo/${business.business_pic}`
                                        : '/images/blank-businesspic.jpg'
                                }
                                width="0"
                                height="0"
                                sizes="640px, 100vw"
                                className="w-full h-64 object-cover rounded-lg"
                            />
                        </div>
                    </div>
                </div>
                <div className="relative">
                    <div className="absolute top-3 right-2">
                        <UpdateBusinessModal
                            _id={business?._id}
                            name={business?.name}
                            address={business?.address}
                            city={business?.city}
                            state={business?.state}
                            latitude={business?.latitude}
                            longitude={business?.longitude}
                            categories={business?.categories}
                            description={business?.description}
                            business_pic={business?.business_pic}
                        />
                    </div>
                </div>
                <div className="text-center mt-5">
                    <h3 className="text-4xl font-semibold leading-normal mb-2 text-gray-900 px-10">
                        {business?.name}
                    </h3>
                    <Link
                        href={`https://www.google.com/maps/place/${business?.latitude},${business?.longitude}`}>
                        <div className="text-blue-500 underline mt-3 flex flex-row justify-center items-center">
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke-width="1.5"
                                stroke="currentColor"
                                className="w-6 h-6 mr-2">
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"
                                />
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"
                                />
                            </svg>
                            {business?.address}, {business?.city}
                        </div>
                        <div className="mb-2 text-blue-500 underline">
                            <i className="fas fa-university mr-2 text-lg text-gray-900"></i>
                            {business?.state}
                        </div>
                    </Link>
                    <div className="flex flex-wrap justify-center mt-5">
                        {business?.categories
                            .split(', ')
                            .map((category, index) => (
                                <span
                                    key={index}
                                    className="badge bg-[#39c1f6] text-[#f7fafc] badge-lg mr-3 mb-3">
                                    {category}
                                </span>
                            ))}
                    </div>
                </div>
                <div className="mt-10 py-10 border-t border-gray-200 text-center">
                    <div className="flex flex-wrap justify-center">
                        <div className="w-full px-10">
                            <p className="mb-4 text-lg text-justify leading-relaxed text-gray-900">
                                {showMore ? fullDescription : shortDescription}
                            </p>
                            <a
                                href="#pablo"
                                className="font-normal text-gray-500"
                                onClick={handleShowMoreClick}>
                                {showMore ? 'Show less' : 'Show more'}
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}

export default CardProfile;
